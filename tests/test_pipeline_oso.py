from datetime import datetime, timezone
from pathlib import Path

from fpm.domain import ApprovalDecision
from fpm.oso.client import FakeOsoClient
from fpm.pipeline import run_review
from fpm.store import JsonlRecordStore
from fpm.synthesize import FakeReviewSynthesizer

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
ROWS = [{"date": 300, "tvl": 3_900_000, "_dlt_load_id": "L", "_dlt_id": "a"}]


def test_oso_manifest_end_to_end(tmp_path):
    client = FakeOsoClient(run_status="SUCCESS", query_rows=ROWS)
    store = JsonlRecordStore(tmp_path)
    bundles = run_review(
        manifest_path="tests/fixtures/chainsafe_oso.yaml",
        fixtures_dir=Path("fixtures/responses"),
        synthesizer=FakeReviewSynthesizer(),
        store=store,
        decide=lambda r: ApprovalDecision(action="approve", approver="carl"),
        as_of=AS_OF,
        oso_client=client,
        org_id="org",
        allowlist={"api.llama.fi"},
    )
    assert len(bundles) == 1
    rec = bundles[0].recommendation
    assert rec.sla_outcome == "pass" and rec.review_status == "meeting"
    assert (
        rec.citations[0].evidence_bundle_hash
        == bundles[0].dossier.reading.claim.evidence.evidence_bundle_hash
    )


def test_fixture_manifest_still_runs_without_client(tmp_path):
    store = JsonlRecordStore(tmp_path)
    bundles = run_review(
        manifest_path="tests/fixtures/chainsafe.yaml",
        fixtures_dir=Path("fixtures/responses"),
        synthesizer=FakeReviewSynthesizer(),
        store=store,
        decide=lambda r: ApprovalDecision(action="approve", approver="carl"),
        as_of=AS_OF,
    )
    assert len(bundles) == 2  # Plan 1 behavior intact
