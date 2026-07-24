"""Static PR gate: schema + config-translation + base-ref egress + goalpost report.

Judgment lives here (tested); the workflow YAML is glue. Never fetches anything live.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from fpm.domain import window_for
from fpm.governance.allowlist import host_allowed, load_allowlist
from fpm.governance.classify import classify
from fpm.governance.diff import manifest_diff
from fpm.kernel import conformance_error, load_kernel
from fpm.manifest import Manifest, ManifestError, load_manifest
from fpm.provision import build_ingestion_config
from fpm.transform.validate import TransformSqlError, validate_transform_sql
from scripts.pr_report import render_report


def validate_manifest(
    base: Manifest | None, head: Manifest, allowlist: set[str], as_of: datetime
) -> tuple[bool, str]:
    problems: list[str] = []
    for fn in head.functions:
        if fn.source.kind == "fixture":
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
        err = conformance_error(fn.tier, fn.category, fn.sub_category, kernel, fn.kernel_function)
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="validate_pr")
    ap.add_argument("head", help="path to the head (PR) manifest")
    ap.add_argument("--base", default="", help="path to the base manifest (empty for a new file)")
    ap.add_argument("--allowlist", default="registry/_allowlist.txt")
    ap.add_argument("--as-of", default="2026-07-01")
    ap.add_argument(
        "--summary",
        default="",
        help="path to write the markdown summary (e.g. $GITHUB_STEP_SUMMARY)",
    )
    args = ap.parse_args(argv)
    as_of = datetime.fromisoformat(args.as_of).replace(tzinfo=timezone.utc)
    allowlist = load_allowlist(args.allowlist)
    try:
        head = load_manifest(args.head)
        base = load_manifest(args.base) if args.base else None
    except ManifestError as exc:
        md = f"### Validation failed\n\nschema error: {exc}"
        ok = False
    else:
        ok, md = validate_manifest(base, head, allowlist, as_of)
    if args.summary:
        Path(args.summary).open("a").write(md + "\n")
    print(md)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
