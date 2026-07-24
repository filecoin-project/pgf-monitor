"""Validate and bind a maintainer transform SQL over the per-function raw table.

The contract: exactly one SELECT statement, a single scalar projection, and every table reference
is the bound `raw` alias. Exfiltration is blocked structurally (any other table is rejected), not
by a keyword blocklist. bind_transform_sql then rewrites the `raw` alias to the real qualified
table and substitutes window bind tokens with timestamp literals we own, so the maintainer never
injects a table name or a value we do not control.

Bind tokens come in two flavours matched to the raw column's type:
- :window_start / :window_end / :now  -> tz-naive TIMESTAMP literals. Use with epoch columns via
  from_unixtime(...), which also yields a naive timestamp.
- :window_start_tz / :window_end_tz / :now_tz -> TIMESTAMP WITH TIME ZONE literals (UTC). Use with
  columns dlt parsed from ISO date strings, which land as `timestamp with time zone`.

CTEs are not supported: a CTE reference counts as a table other than `raw` and is therefore
rejected by the table check.
"""

from __future__ import annotations

from datetime import datetime

import sqlglot
from sqlglot import exp

RAW_ALIAS = "raw"
_NAIVE_TOKENS = ("window_start", "window_end", "now")
_TZ_SUFFIX = "_tz"
BIND_TOKENS = _NAIVE_TOKENS + tuple(t + _TZ_SUFFIX for t in _NAIVE_TOKENS)


class TransformSqlError(ValueError):
    """Raised when a transform SQL violates the safety contract."""


def validate_transform_sql(sql: str, raw_alias: str = RAW_ALIAS) -> exp.Expression:
    """Parse and check the SQL. Return the parsed AST on success; raise TransformSqlError otherwise."""
    try:
        statements = [s for s in sqlglot.parse(sql, dialect="trino") if s is not None]
    except Exception as exc:  # parse error
        raise TransformSqlError(f"could not parse SQL: {exc}") from exc
    if len(statements) != 1:
        raise TransformSqlError(f"expected exactly one statement, found {len(statements)}")
    tree = statements[0]
    if not isinstance(tree, exp.Select):
        raise TransformSqlError(f"only a single SELECT is allowed, found {type(tree).__name__}")
    tables = {t.name.lower() for t in tree.find_all(exp.Table)}
    if tables != {raw_alias.lower()}:
        foreign = sorted(tables - {raw_alias.lower()}) or ["(no table)"]
        raise TransformSqlError(
            f"transform may reference only the bound `{raw_alias}` table; found {foreign}"
        )
    if len(tree.expressions) != 1:
        raise TransformSqlError(
            f"transform must select exactly one column (the metric), found {len(tree.expressions)}"
        )
    unknown = sorted(p.name for p in tree.find_all(exp.Placeholder) if p.name not in BIND_TOKENS)
    if unknown:
        raise TransformSqlError(
            f"unknown bind token(s) {unknown}; only {list(BIND_TOKENS)} are supported"
        )
    return tree


def bind_transform_sql(
    tree: exp.Expression,
    raw_full_name: str,
    window_start: datetime,
    window_end: datetime,
    now: datetime,
    raw_alias: str = RAW_ALIAS,
) -> str:
    """Rewrite the validated AST: bound `raw` table -> the real name; bind tokens -> owned literals."""
    values_by_token = {"window_start": window_start, "window_end": window_end, "now": now}

    def rewrite(node: exp.Expression) -> exp.Expression:
        if isinstance(node, exp.Table) and node.name.lower() == raw_alias.lower():
            return exp.to_table(raw_full_name)
        if isinstance(node, exp.Placeholder) and node.name in BIND_TOKENS:
            is_tz = node.name.endswith(_TZ_SUFFIX)
            base = node.name[: -len(_TZ_SUFFIX)] if is_tz else node.name
            stamp = values_by_token[base].strftime("%Y-%m-%d %H:%M:%S")
            if is_tz:
                return exp.cast(exp.Literal.string(f"{stamp} +00:00"), "TIMESTAMP WITH TIME ZONE")
            return exp.cast(exp.Literal.string(stamp), "TIMESTAMP")
        return node

    return tree.transform(rewrite).sql(dialect="trino")
