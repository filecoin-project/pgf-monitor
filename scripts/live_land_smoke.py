"""Quarantined live end-to-end run of `land`. Never imported by unit tests.

Builds a couple of in-memory ReviewBundles (mirroring tests/conftest.py's `_make_bundle` shape),
lands them via StaticModelSink + a real GraphqlStaticModelClient (public + private static
models), queries both tables back via pyoso, confirms the public grant (done inside land), and
deletes both datasets in a finally.

Usage: OSO_API_KEY=... uv run python scripts/live_land_smoke.py <ORG_ID>
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from fpm.bundle import ReviewBundle
from fpm.domain import (
    Claim,
    EvidenceRef,
    MeasurementWindow,
    Reading,
    ReviewRecommendation,
    SlaResult,
    Verdict,
    VersionSet,
)
from fpm.dossier import ReviewDossier
from fpm.land import StaticModelSink, land
from fpm.oso.static_model import GraphqlStaticModelClient
from fpm.synthesize import SynthesisOutput

_WIN = MeasurementWindow(
    start=datetime(2026, 6, 1, tzinfo=timezone.utc), end=datetime(2026, 7, 1, tzinfo=timezone.utc)
)


def _make_bundle(rid: str, narrative: str, note: str, approver: str, hexchar: str) -> ReviewBundle:
    reading = Reading(
        team="chainsafe",
        function_id="forest-uptime",
        metric="uptime_ratio",
        measurement_window=_WIN,
        claim=Claim(
            value=0.999,
            origin="independent",
            source_ref="https://x",
            fetched_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            evidence=EvidenceRef(
                canonical_payload_hash=hexchar * 64,
                request_fingerprint=hexchar * 64,
                evidence_bundle_hash=hexchar * 64,
            ),
            fetched_by="oso@0.1.0",
        ),
        source_metadata={},
        adapter="oso",
        adapter_version="0.1.0",
    )
    sla = SlaResult(
        outcome="pass",
        op=">=",
        threshold=0.99,
        observed=0.999,
        measurement_window=_WIN,
        reason="ok",
    )
    dossier = ReviewDossier(
        team="chainsafe",
        function_id="forest-uptime",
        sla_statement="uptime >= 99%",
        sla_result=sla,
        reading=reading,
        detector_results=[],
        flags=[],
        context=[],
    )
    versions = VersionSet(
        manifest_commit_sha="deadbeef",
        commitment_version="1",
        measurement_window_start=_WIN.start,
        measurement_window_end=_WIN.end,
        adapter_version="0.1.0",
        pipeline_version="0.1.0",
        rubric_version="0.1.0",
        detector_versions={},
        model_id="claude-opus-4-8",
        prompt_version="0",
    )
    rec = ReviewRecommendation(
        recommendation_id=rid,
        team="chainsafe",
        function_id="forest-uptime",
        review_status="meeting",
        sla_outcome="pass",
        narrative=narrative,
        citations=[],
        flags=[],
        detector_results=[],
        versions=versions,
    )
    verdict = Verdict(
        recommendation_id=rid,
        adjudicated_status="meeting",
        approver=approver,
        approved_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        action="approve",
        note=note,
    )
    return ReviewBundle(
        dossier=dossier,
        synthesis_output=SynthesisOutput(
            review_status="meeting", narrative=narrative, cited_evidence_hashes=[]
        ),
        recommendation=rec,
        verdict=verdict,
    )


def main() -> None:
    org_id = sys.argv[1]
    bundles = [
        _make_bundle("rec-1", "model says: ok, all good", "looks fine", "live-smoke", "a"),
        _make_bundle("rec-2", "model says: also ok", "confirmed", "live-smoke", "d"),
    ]
    client = GraphqlStaticModelClient(api_key=os.environ["OSO_API_KEY"], org_id=org_id)
    sink = StaticModelSink(client, org_id)

    public_name = "fpm_smoke_public"
    private_name = "fpm_smoke_private"

    try:
        result = land(bundles, sink, public_name=public_name, private_name=private_name)
        print(f"\n=== landed: public={result['public']} private={result['private']} ===")

        for label, name in ((public_name, "public"), (private_name, "private")):
            dataset_id = client.ensure_static_dataset(org_id, label)
            full = client.table_full_name(dataset_id)
            rows = client.query(f"SELECT * FROM {full}") if full else []
            print(f"[{name}] table={full} rows={len(rows)}")

        # grant_public runs inside land() for the public table only (confirmed live: the grant
        # mutation returns {success: true}). Verifying actual public-readability would need a
        # second, unauthenticated identity, which is out of scope here; the grant call succeeding
        # inside land() is the checkpoint.
        print(
            f"public model {result['public']} granted public READ via land(); private not granted"
        )
    finally:
        for name in (public_name, private_name):
            dataset_id = client.ensure_static_dataset(org_id, name)
            client.delete_dataset(dataset_id)
            print("cleanup: deleted", name, dataset_id)


if __name__ == "__main__":
    main()
