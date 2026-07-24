"""Quarantined live end-to-end run of the full `review` workflow. Never imported by unit tests.

Runs run_review over registry/chainsafe.yaml against real OSO ingestion + a real model
synthesizer: for every kernel function it fetches from the real source, evaluates the SLA
(extract or transform), runs detectors, gets a bounded model judgment, adjudicates
(auto-approve), and persists ReviewBundle verdicts. Datasets it provisions are deleted at the end.

Usage: OSO_API_KEY=... uv run python scripts/live_review_smoke.py <ORG_ID>
Requires OSO ingestion credentials and ANTHROPIC/Vertex credentials for the synthesizer.
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fpm.domain import ApprovalDecision
from fpm.governance.allowlist import load_allowlist
from fpm.manifest import load_manifest
from fpm.oso.graphql_client import GraphqlOsoClient
from fpm.pipeline import run_review
from fpm.provision import dataset_name
from fpm.store import JsonlRecordStore
from fpm.synthesize import SdkReviewSynthesizer

MANIFEST = "registry/chainsafe.yaml"


def main() -> None:
    org_id = sys.argv[1]
    as_of = datetime(2026, 7, 14, tzinfo=timezone.utc)
    manifest = load_manifest(MANIFEST)
    allowlist = load_allowlist("registry/_allowlist.txt")
    client = GraphqlOsoClient(api_key=os.environ["OSO_API_KEY"], org_id=org_id)
    store = JsonlRecordStore(Path(tempfile.mkdtemp(prefix="fpm-review-")))

    try:
        bundles = run_review(
            manifest_path=MANIFEST,
            fixtures_dir=Path("fixtures/responses"),
            synthesizer=SdkReviewSynthesizer(model_id="claude-opus-4-8", prompt_version="0"),
            store=store,
            decide=lambda r: ApprovalDecision(action="approve", approver="live-smoke"),
            as_of=as_of,
            manifest_commit_sha=os.environ.get("FPM_COMMIT", "live"),
            oso_client=client,
            org_id=org_id,
            allowlist=allowlist,
            poll_sleep=10.0,
        )
        print(f"\n=== {len(bundles)} verdicts persisted ===")
        for b in bundles:
            r = b.recommendation
            flags = ",".join(f.type for f in r.flags) or "-"
            print(f"\n[{r.function_id}] sla={r.sla_outcome} review={r.review_status} flags={flags}")
            print(f"    {r.narrative[:200]}")
    finally:
        # provisioned datasets are durable (reused across runs); delete them to leave the org clean
        for fn in manifest.functions:
            dsid = client.find_dataset(org_id, dataset_name(manifest.team, fn.function_id))
            if dsid:
                client.delete_dataset(dsid)


if __name__ == "__main__":
    main()
