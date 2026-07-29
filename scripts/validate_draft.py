"""Validate draft manifests (registry/drafts/*.yaml) offline.

Runs the same checks the PR gate would run after promotion: schema, kernel-triple
conformance, transform-SQL validation, allowlist membership. Allowlist misses are
reported but only fail with --strict (drafts are expected to need additions — they
are listed in each draft's x_draft.allowlist_additions).

Usage:
  uv run python scripts/validate_draft.py registry/drafts/<team>.yaml [...]
  uv run python scripts/validate_draft.py --all
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fpm.drafts import promotion_problems, split_draft
from fpm.governance.allowlist import load_allowlist
from fpm.kernel import load_kernel
from fpm.manifest import ManifestError


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="validate_draft")
    ap.add_argument("paths", nargs="*", help="draft file(s) to validate")
    ap.add_argument("--all", action="store_true", help="validate every registry/drafts/*.yaml")
    ap.add_argument("--allowlist", default="registry/_allowlist.txt")
    ap.add_argument(
        "--strict", action="store_true", help="treat allowlist misses as failures (promotion mode)"
    )
    args = ap.parse_args(argv)

    paths = [Path(p) for p in args.paths]
    if args.all:
        paths += sorted(Path("registry/drafts").glob("*.yaml"))
    if not paths:
        if args.all:
            print(
                "no drafts in registry/drafts/ — nothing to validate (all promoted to registry/)."
            )
            return 0
        ap.error("no drafts given (pass paths or --all)")

    allowlist = load_allowlist(args.allowlist)
    kernel = load_kernel()
    failed = False
    for path in paths:
        try:
            manifest, x_draft = split_draft(path)
        except ManifestError as exc:
            print(f"FAIL {path}: schema error: {exc}")
            failed = True
            continue
        problems = promotion_problems(manifest, kernel, allowlist)
        hard = [p for p in problems if "allowlist" not in p]
        soft = [p for p in problems if "allowlist" in p]
        for p in hard:
            print(f"FAIL {path}: {p}")
        for p in soft:
            marker = "FAIL" if args.strict else "note"
            print(f"{marker} {path}: {p} — needs a committee allowlist addition")
        unmeasured = len(x_draft.get("unmeasured") or [])
        if not hard and not (args.strict and soft):
            print(
                f"OK   {path}: {len(manifest.functions)} function(s), "
                f"{unmeasured} unmeasured, {len(soft)} pending allowlist host(s)"
            )
        failed = failed or bool(hard) or (args.strict and bool(soft))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
