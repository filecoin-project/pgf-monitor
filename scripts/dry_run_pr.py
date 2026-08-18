"""Committee-labeled live dry-run over CHANGED functions only. Client injected (fake in tests).

Re-checks egress against the base allowlist so a label cannot smuggle an off-allowlist endpoint.

The measurement runs through the real OsoAdapter, so what the gate proves is what the nightly
will do — extract and transform alike, read back the same way. It provisions its OWN dataset,
named for the run, and deletes only that: reusing the durable name and deleting it in a
`finally` (as this script once did) destroyed the production dataset for every function a
labelled PR touched, and an authenticated source cannot be recreated by the nightly runner,
which holds no credential.
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

from fpm.adapters.oso import OsoAdapter
from fpm.domain import window_for
from fpm.governance.diff import manifest_diff
from fpm.governance.fields import bucket_for
from fpm.manifest import Manifest
from fpm.provision import EgressError, MissingSecretError, dataset_name

_TAG = re.compile(r"^[a-z0-9][a-z0-9_]*$")


def changed_function_ids(base: Manifest | None, head: Manifest) -> set[str]:
    """Which functions this PR needs live proof for, derived from the semantic diff.

    A manifest-level change (a `team` rename) carries no function_id and would otherwise select
    nothing — but `team` names the OSO dataset and keys every observation and threshold row, so it
    re-points every measurement the manifest makes. Those changes select ALL functions.
    """
    if base is None:
        return {f.function_id for f in head.functions}
    changes = manifest_diff(base, head)
    if any(not c.function_id and bucket_for(c.field_path) == "material" for c in changes):
        return {f.function_id for f in head.functions}
    return {c.function_id for c in changes if c.function_id}


def ephemeral_name(team: str, function_id: str, run_tag: str) -> str:
    """The durable name plus the run's own suffix. Never equal to a durable name."""
    return f"{dataset_name(team, function_id)}_{run_tag}"


def resolve_as_of(value: str) -> datetime:
    """Empty means now. The gate proves a metric works today, not on some pinned date."""
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def _one(fn, team, client, org_id, allowlist, as_of, poll_sleep, run_tag) -> tuple[bool, str]:
    window = window_for(fn.sla.cadence, as_of)
    name = ephemeral_name(team, fn.function_id, run_tag)
    adapter = OsoAdapter(
        client,
        org_id=org_id,
        allowlist=allowlist,
        poll_sleep=poll_sleep,
        dataset_namer=lambda t, f: ephemeral_name(t, f, run_tag),
    )
    try:
        reading = adapter.fetch(fn, team, window)
    except EgressError as exc:
        return False, f"{fn.function_id}: egress not allowed ({exc})"
    except MissingSecretError as exc:
        # The runner holds no credential for this source, so the gate cannot prove it either
        # way. Say so rather than reporting a pass it did not earn.
        return False, f"{fn.function_id}: cannot be proven here ({exc})"
    except Exception as exc:  # noqa: BLE001 — one function must not abort the whole gate
        return False, f"{fn.function_id}: {type(exc).__name__}: {exc}"
    finally:
        # Only ever the name this run created. A leftover from a crashed earlier run on the
        # same PR is cleaned up here too.
        stale = client.find_dataset(org_id, name)
        if stale is not None:
            client.delete_dataset(stale)

    status = reading.source_metadata.get("run_status")
    if status != "SUCCESS":
        return False, f"{fn.function_id}: run did not succeed ({status})"
    error = reading.source_metadata.get("transform_error")
    if error:
        return False, f"{fn.function_id}: {error}"
    if reading.claim.value is None:
        return False, f"{fn.function_id}: no value read back"
    return True, f"{fn.function_id}: observed {reading.claim.value}"


def dry_run(
    head,
    changed,
    client,
    org_id,
    allowlist,
    as_of: datetime,
    poll_sleep: float = 0.0,
    run_tag: str = "dryrun",
):
    if not _TAG.match(run_tag):
        raise ValueError(
            f"run_tag {run_tag!r} must match {_TAG.pattern} — it suffixes the dataset name, and "
            "an empty or odd tag is how a throwaway dataset ends up sharing a durable one's name"
        )
    lines, ok = [], True
    for fn in head.functions:
        if fn.function_id not in changed or fn.source.kind == "fixture":
            continue
        passed, msg = _one(fn, head.team, client, org_id, allowlist, as_of, poll_sleep, run_tag)
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
    ap.add_argument("--as-of", default="", help="measurement date (default: today, UTC)")
    ap.add_argument("--oso-org", default="", help="OSO org id (falls back to OSO_ORG_ID env var)")
    ap.add_argument(
        "--run-tag",
        default="dryrun",
        help="suffix for the throwaway dataset names, e.g. pr123 (lowercase, digits, underscore)",
    )
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

    as_of = resolve_as_of(args.as_of)
    allowlist = load_allowlist(args.allowlist)
    head = load_manifest(args.head)
    base = load_manifest(args.base) if args.base else None
    changed = changed_function_ids(base, head)
    org_id = args.oso_org or os.environ["OSO_ORG_ID"]
    client = GraphqlOsoClient(api_key=os.environ["OSO_API_KEY"], org_id=org_id)

    ok, md = dry_run(
        head, changed, client, org_id, allowlist, as_of, poll_sleep=10.0, run_tag=args.run_tag
    )
    if args.summary:
        Path(args.summary).open("a").write(md + "\n")
    print(md)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
