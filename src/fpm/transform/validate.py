"""Validate and bind maintainer SQL — over the per-function raw table, or over the warehouse.

Two regimes, one shared contract: exactly one SELECT statement, a single scalar projection, and
only bind tokens we own. They differ in which tables may be named, and that difference is the
whole safety story:

- `validate_transform_sql` (kind `http-json`) binds the ONE `raw` table the function's own
  ingestion landed. Any other table is rejected, so a transform can only ever read the response
  its own source fetched.
- `validate_warehouse_sql` (kind `oso-sql`) reads tables that are ALREADY in the warehouse, so
  there is no `raw` to bind against. Instead every table reference must be fully qualified AND on
  `registry/_sql_allowlist.txt`. That list is committee-maintained, CODEOWNERS-guarded, and read
  from the BASE ref rather than the PR head — the same discipline as the egress host allowlist,
  and for a sharper reason: the provisioning host's OSO_API_KEY is org-scoped, so unrestricted
  warehouse SQL could lift `filpgf_private.*` or `funding_model_static.applicant_identity` into a
  PUBLIC observation value.

Exfiltration is blocked structurally in both cases (any unlisted table is rejected), never by a
keyword blocklist. "Structurally" carries a second requirement that is easy to get wrong: the
check must run over the reference's own identifier parts, so that the name being checked is
always the name that executes. See `table_refs` for the two ways a re-joined string diverges
from the reference Trino receives — that is the one way this guard fails silently.

Binding then substitutes window tokens with timestamp literals we own, so the maintainer never
injects a table name or a value we do not control.

Bind tokens come in two flavours matched to the column's type:
- :window_start / :window_end / :now  -> tz-naive TIMESTAMP literals. Use with epoch columns via
  from_unixtime(...), which also yields a naive timestamp.
- :window_start_tz / :window_end_tz / :now_tz -> TIMESTAMP WITH TIME ZONE literals (UTC). Use with
  columns dlt parsed from ISO date strings, which land as `timestamp with time zone`.

CTEs are not supported in either regime: a CTE reference counts as a table, and it is neither the
bound `raw` alias nor a fully-qualified allowlisted name, so the table check rejects it. Inline
subqueries are fine — they name real tables, which are checked like any other.
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
    """Raised when a transform or warehouse SQL violates the safety contract."""


def _parse_one_select(sql: str) -> exp.Select:
    """Parse and require exactly one SELECT statement."""
    try:
        statements = [s for s in sqlglot.parse(sql, dialect="trino") if s is not None]
    except Exception as exc:  # parse error
        raise TransformSqlError(f"could not parse SQL: {exc}") from exc
    if len(statements) != 1:
        raise TransformSqlError(f"expected exactly one statement, found {len(statements)}")
    tree = statements[0]
    if not isinstance(tree, exp.Select):
        raise TransformSqlError(f"only a single SELECT is allowed, found {type(tree).__name__}")
    return tree


def _check_scalar_and_tokens(tree: exp.Select) -> None:
    """Require a single scalar projection and only bind tokens we own."""
    if len(tree.expressions) != 1:
        raise TransformSqlError(
            f"transform must select exactly one column (the metric), found {len(tree.expressions)}"
        )
    # `SELECT *` is ONE projection to the parser but any number of columns at runtime, so the
    # count above waves it through and only the adapter's single-cell check catches it — as a
    # permanent `indeterminate` nobody diagnoses. Fail at PR time instead.
    if any(isinstance(e, exp.Star) for e in tree.expressions):
        raise TransformSqlError("`SELECT *` is not a single scalar; name the metric expression")
    unknown = sorted(p.name for p in tree.find_all(exp.Placeholder) if p.name not in BIND_TOKENS)
    if unknown:
        raise TransformSqlError(
            f"unknown bind token(s) {unknown}; only {list(BIND_TOKENS)} are supported"
        )


def table_refs(tree: exp.Expression) -> list[tuple[str, ...]]:
    """Every table reference as its faithful, lowercased identifier parts.

    Built from `exp.Table.parts`, and NOT from `catalog`/`db`/`name`, because those three
    attributes are a LOSSY projection of the reference. For a name with more than three parts
    sqlglot keeps first/second/last, so the middle silently disappears from anything built out of
    them while surviving verbatim into the SQL we execute. That divergence made
    `filecoin.data_portal.filpgf_private.filecoin_pay_rails` check as the allowlisted
    `filecoin.data_portal.filecoin_pay_rails`. A quoted identifier can also carry dots INSIDE one
    part (`"filecoin.data_portal".filecoin_pay_rails`), which joins back to the same allowlisted
    string while resolving against a different catalog at query time. Both are why the caller
    must inspect the parts, never a re-joined string.
    """
    return [tuple(part.name.lower() for part in t.parts) for t in tree.find_all(exp.Table)]


def qualified_tables(tree: exp.Expression) -> set[str]:
    """The dotted form of every table reference. Reporting only — check with `table_refs`."""
    return {".".join(ref) for ref in table_refs(tree)}


def validate_transform_sql(sql: str, raw_alias: str = RAW_ALIAS) -> exp.Expression:
    """Parse and check the SQL. Return the parsed AST on success; raise TransformSqlError otherwise."""
    tree = _parse_one_select(sql)
    tables = {t.name.lower() for t in tree.find_all(exp.Table)}
    if tables != {raw_alias.lower()}:
        foreign = sorted(tables - {raw_alias.lower()}) or ["(no table)"]
        raise TransformSqlError(
            f"transform may reference only the bound `{raw_alias}` table; found {foreign}"
        )
    _check_scalar_and_tokens(tree)
    return tree


def validate_warehouse_sql(sql: str, allowed_tables: set[str]) -> exp.Expression:
    """Check SQL that reads warehouse tables directly. Every table must be allowlisted.

    Returns the parsed AST on success; raises TransformSqlError otherwise. `allowed_tables` is
    normalized here so a caller cannot weaken the check by passing mixed case or stray whitespace.
    """
    tree = _parse_one_select(sql)
    allowed = {a.strip().lower() for a in allowed_tables if a and a.strip()}
    refs = table_refs(tree)
    if not refs:
        raise TransformSqlError("warehouse SQL must reference at least one table")
    # Exactly three parts, none of them empty and none containing a dot of its own. Anything else
    # cannot be checked against the allowlist honestly: an unqualified name says nothing about
    # which catalog and schema it resolves to, a four-part name checks as a three-part one, and a
    # quoted part carrying dots re-joins to a string that is not the reference Trino will see.
    # This is also what rejects CTE aliases, quoted or not.
    malformed = sorted(
        ".".join(r) for r in refs if len(r) != 3 or any(("." in part or not part) for part in r)
    )
    if malformed:
        raise TransformSqlError(
            "every table must be fully qualified as exactly catalog.schema.table, with no dot "
            f"inside a quoted identifier (and CTEs are not supported); found {malformed}"
        )
    foreign = sorted({".".join(r) for r in refs} - allowed)
    if foreign:
        raise TransformSqlError(
            f"table(s) {foreign} are not on the warehouse allowlist; a committee addition to "
            "registry/_sql_allowlist.txt must land in an EARLIER pull request"
        )
    _check_scalar_and_tokens(tree)
    return tree


def _token_literal(name: str, values_by_token: dict[str, datetime]) -> exp.Expression:
    is_tz = name.endswith(_TZ_SUFFIX)
    base = name[: -len(_TZ_SUFFIX)] if is_tz else name
    stamp = values_by_token[base].strftime("%Y-%m-%d %H:%M:%S")
    if is_tz:
        return exp.cast(exp.Literal.string(f"{stamp} +00:00"), "TIMESTAMP WITH TIME ZONE")
    return exp.cast(exp.Literal.string(stamp), "TIMESTAMP")


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
            return _token_literal(node.name, values_by_token)
        return node

    return tree.transform(rewrite).sql(dialect="trino")


def bind_warehouse_sql(
    tree: exp.Expression,
    window_start: datetime,
    window_end: datetime,
    now: datetime,
) -> str:
    """Rewrite bind tokens into owned literals. Table names are already real and allowlisted."""
    values_by_token = {"window_start": window_start, "window_end": window_end, "now": now}

    def rewrite(node: exp.Expression) -> exp.Expression:
        if isinstance(node, exp.Placeholder) and node.name in BIND_TOKENS:
            return _token_literal(node.name, values_by_token)
        return node

    return tree.transform(rewrite).sql(dialect="trino")
