"""Static PR gate: schema + config-translation + base-ref egress + goalpost report.

Judgment lives here (tested); the workflow YAML is glue. Never fetches anything live.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from fpm.domain import window_for
from fpm.governance.allowlist import host_allowed, load_allowlist, load_sql_allowlist
from fpm.governance.classify import classify
from fpm.governance.diff import manifest_diff
from fpm.kernel import conformance_error, load_kernel
from fpm.manifest import Manifest, ManifestError, load_manifest
from fpm.provision import build_ingestion_config
from fpm.transform.validate import (
    TransformSqlError,
    validate_transform_sql,
    validate_warehouse_sql,
)
from scripts.pr_report import render_report


def validate_manifest(
    base: Manifest | None,
    head: Manifest,
    allowlist: set[str],
    as_of: datetime,
    sql_allowlist: set[str] | None = None,
) -> tuple[bool, str]:
    problems: list[str] = []
    for fn in head.functions:
        if fn.source.kind == "fixture":
            continue
        if fn.source.kind == "oso-sql":
            # Nothing is fetched, so there is no host to check and no ingestion config to
            # translate. The equivalent gate is the table allowlist, and like the host list it is
            # read from the BASE ref -- a table added in this same PR is not yet trusted.
            try:
                validate_warehouse_sql(fn.source.sql, sql_allowlist or set())
            except TransformSqlError as exc:
                problems.append(f"{fn.function_id}: warehouse SQL rejected ({exc})")
            continue
        if not host_allowed(fn.source.base_url, allowlist):
            problems.append(
                f"{fn.function_id}: base_url host not on allowlist ({fn.source.base_url})"
            )
            continue
        try:
            build_ingestion_config(fn, window_for(fn.sla.cadence, as_of), head.team)
        except Exception as exc:  # translation must succeed
            problems.append(f"{fn.function_id}: config translation failed ({exc})")
        if fn.transform is not None:
            try:
                validate_transform_sql(fn.transform.sql)
            except TransformSqlError as exc:
                problems.append(f"{fn.function_id}: transform SQL rejected ({exc})")
    kernel = load_kernel()
    for fn in head.functions:
        err = conformance_error(fn.tier, fn.category, fn.sub_category, kernel, fn.kernel_id)
        if err is not None:
            problems.append(f"{fn.function_id}: {err}")
    report = render_report(classify(manifest_diff(base, head), head) if base else [])
    ok = not problems
    md = (
        report
        if ok
        else "### Validation failed\n\n" + "\n".join(f"- {p}" for p in problems) + "\n\n" + report
    )
    return ok, md


def validate_removal(base: Manifest, head_path: str) -> tuple[bool, str]:
    """A manifest deleted in this PR.

    Removing a commitment is a governance event the committee must SEE, not a crash. The
    workflow feeds every changed path under registry/ to this script as `head`, including
    deleted ones, so diff the base against an empty head: every function then classifies as
    `removed` -> MATERIAL via the same rubric a threshold change goes through.

    Returns ok=True — a removal is a legitimate change requiring review, not a rule violation.
    """
    empty = base.model_copy(update={"functions": []})
    report = render_report(classify(manifest_diff(base, empty), empty))
    return True, (
        f"### Manifest removed: `{head_path}`\n\n"
        f"{len(base.functions)} function(s) are no longer monitored. "
        "Confirm this is intended before merging.\n\n" + report
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="validate_pr")
    ap.add_argument("head", help="path to the head (PR) manifest")
    ap.add_argument("--base", default="", help="path to the base manifest (empty for a new file)")
    ap.add_argument("--allowlist", default="registry/_allowlist.txt")
    ap.add_argument("--sql-allowlist", default="registry/_sql_allowlist.txt")
    ap.add_argument("--as-of", default="2026-07-01")
    ap.add_argument(
        "--summary",
        default="",
        help="path to write the markdown summary (e.g. $GITHUB_STEP_SUMMARY)",
    )
    args = ap.parse_args(argv)
    as_of = datetime.fromisoformat(args.as_of).replace(tzinfo=timezone.utc)
    allowlist = load_allowlist(args.allowlist)
    # Missing is treated as empty, not as permissive: a checkout whose base predates this
    # file must reject every warehouse table rather than accept every one.
    sql_path = Path(args.sql_allowlist)
    sql_allowlist = load_sql_allowlist(sql_path) if sql_path.exists() else set()
    try:
        if not Path(args.head).exists():
            if not args.base:
                raise ManifestError(f"{args.head}: neither head nor base exists")
            ok, md = validate_removal(load_manifest(args.base), args.head)
        else:
            head = load_manifest(args.head)
            base, base_note = None, ""
            if args.base:
                try:
                    base = load_manifest(args.base)
                except ManifestError as exc:
                    # The base predates a schema migration in this PR, so the current loader
                    # cannot read it. A goalpost diff against an unreadable base is impossible,
                    # but the HEAD manifest is still fully validated below -- so this is a
                    # missing comparison, not an invalid PR. Say so instead of failing.
                    base_note = (
                        "> **No goalpost diff.** The base manifest does not validate against this "
                        f"PR's schema (`{exc}`), which is what a schema migration looks like. "
                        "Head is validated in full; the before/after comparison is unavailable "
                        "and every function should be read as new.\n\n"
                    )
            ok, md = validate_manifest(base, head, allowlist, as_of, sql_allowlist)
            md = base_note + md
    except ManifestError as exc:
        md = f"### Validation failed\n\nschema error: {exc}"
        ok = False
    if args.summary:
        Path(args.summary).open("a").write(md + "\n")
    print(md)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
