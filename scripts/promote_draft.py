"""Promote a draft manifest into registry/ proper.

Strips the x_draft block textually (comments survive), optionally appends the draft's
declared allowlist additions, and refuses to write unless the promoted manifest passes
every check the PR gate runs. The promoted file still goes through a real PR — this
script just prepares the working tree.

Usage:
  uv run python scripts/promote_draft.py registry/drafts/<team>.yaml [--add-allowlist]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fpm.drafts import promotion_problems, split_draft, strip_x_draft_text
from fpm.governance.allowlist import load_allowlist
from fpm.kernel import load_kernel
from fpm.manifest import ManifestError


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="promote_draft")
    ap.add_argument("draft", help="registry/drafts/<team>.yaml")
    ap.add_argument("--allowlist", default="registry/_allowlist.txt")
    ap.add_argument(
        "--add-allowlist",
        action="store_true",
        help="append the draft's x_draft.allowlist_additions to the allowlist first",
    )
    ap.add_argument("--out", default="", help="output path (default registry/<team>.yaml)")
    args = ap.parse_args(argv)

    draft_path = Path(args.draft)
    try:
        manifest, x_draft = split_draft(draft_path)
    except ManifestError as exc:
        print(f"schema error: {exc}", file=sys.stderr)
        return 1

    allowlist_path = Path(args.allowlist)
    if args.add_allowlist:
        current = load_allowlist(allowlist_path)
        additions = [h for h in (x_draft.get("allowlist_additions") or []) if h not in current]
        if additions:
            text = allowlist_path.read_text()
            if text and not text.endswith("\n"):
                text += "\n"
            allowlist_path.write_text(text + "".join(h + "\n" for h in additions))
            print(f"allowlist: added {', '.join(additions)}")

    problems = promotion_problems(manifest, load_kernel(), load_allowlist(allowlist_path))
    if problems:
        for p in problems:
            print(f"BLOCKED: {p}", file=sys.stderr)
        print("fix the draft (or pass --add-allowlist) and re-run", file=sys.stderr)
        return 1

    out = Path(args.out) if args.out else Path("registry") / f"{manifest.team}.yaml"
    if out.exists():
        print(f"BLOCKED: {out} already exists — merge by hand", file=sys.stderr)
        return 1
    # x_draft survives as comments so the slate context + unmeasured rationale stay visible
    out.write_text(strip_x_draft_text(draft_path.read_text(), comment=True))
    print(f"promoted {draft_path} -> {out} ({len(manifest.functions)} functions)")
    print("next: delete the draft, open a PR, and let the gate + committee take it from here")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
