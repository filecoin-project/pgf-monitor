"""Committee-labeled live dry-run over CHANGED functions only. Client injected (fake in tests).

Re-checks egress against the base allowlist so a label cannot smuggle an off-allowlist endpoint.
Always deletes the throwaway dataset.
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

from fpm.domain import window_for
from fpm.governance.diff import manifest_diff
from fpm.manifest import Manifest
from fpm.provision import EgressError, assert_egress_allowed, build_ingestion_config, dataset_name
from fpm.reduce import reduce_rows

_TERMINAL = {"SUCCESS", "FAILED", "CANCELED"}


def changed_function_ids(base: Manifest | None, head: Manifest) -> set[str]:
    if base is None:
        return {f.function_id for f in head.functions}
    ids = set()
    for c in manifest_diff(base, head):
        if c.function_id:
            ids.add(c.function_id)
    return ids


def _one(fn, team, client, org_id, allowlist, as_of, poll_sleep) -> tuple[bool, str]:
    try:
        assert_egress_allowed(fn, allowlist)
    except EgressError as exc:
        return False, f"{fn.function_id}: egress not allowed ({exc})"
    window = window_for(fn.sla.cadence, as_of)
    name = dataset_name(team, fn.function_id)
    dataset_id = client.find_dataset(org_id, name) or client.create_dataset(org_id, name, name)
    try:
        client.attach_rest_config(dataset_id, build_ingestion_config(fn, window, team))
        run_id = client.trigger_run(dataset_id)
        run = None
        for _ in range(30):
            run = {r.run_id: r for r in client.get_runs(dataset_id)}.get(run_id)
            if run and run.status in _TERMINAL:
                break
            if poll_sleep:
                time.sleep(poll_sleep)
        if not run or run.status != "SUCCESS":
            return (
                False,
                f"{fn.function_id}: run did not succeed ({run.status if run else 'unknown'})",
            )
        rows = client.query(f"SELECT * FROM {client.table_full_name(dataset_id)}")
        value = reduce_rows(rows, fn.source.extract)
        if value is None:
            return False, f"{fn.function_id}: no value read back"
        return True, f"{fn.function_id}: observed {value}"
    finally:
        client.delete_dataset(dataset_id)


def dry_run(head, changed, client, org_id, allowlist, as_of: datetime, poll_sleep: float = 0.0):
    lines, ok = [], True
    for fn in head.functions:
        if fn.function_id not in changed or fn.source.kind == "fixture":
            continue
        passed, msg = _one(fn, head.team, client, org_id, allowlist, as_of, poll_sleep)
        ok = ok and passed
        lines.append(("PASS " if passed else "FAIL ") + msg)
    md = "### Live dry-run\n\n" + (
        "\n".join(f"- {ln}" for ln in lines) or "- no changed live sources"
    )
    return ok, md


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="dry_run_pr")
    ap.add_argument("head", help="path to the head (PR) manifest")
    ap.add_argument("--base", default="", help="path to the base manifest (empty for a new file)")
    ap.add_argument("--allowlist", default="registry/_allowlist.txt")
    ap.add_argument("--as-of", default="2026-07-01")
    ap.add_argument("--oso-org", default="", help="OSO org id (falls back to OSO_ORG_ID env var)")
    ap.add_argument(
        "--summary",
        default="",
        help="path to write the markdown summary (e.g. $GITHUB_STEP_SUMMARY)",
    )
    args = ap.parse_args(argv)

    import os

    from fpm.governance.allowlist import load_allowlist
    from fpm.manifest import load_manifest
    from fpm.oso.graphql_client import GraphqlOsoClient

    as_of = datetime.fromisoformat(args.as_of).replace(tzinfo=timezone.utc)
    allowlist = load_allowlist(args.allowlist)
    head = load_manifest(args.head)
    base = load_manifest(args.base) if args.base else None
    changed = changed_function_ids(base, head)
    org_id = args.oso_org or os.environ["OSO_ORG_ID"]
    client = GraphqlOsoClient(api_key=os.environ["OSO_API_KEY"], org_id=org_id)

    ok, md = dry_run(head, changed, client, org_id, allowlist, as_of, poll_sleep=10.0)
    if args.summary:
        Path(args.summary).open("a").write(md + "\n")
    print(md)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
