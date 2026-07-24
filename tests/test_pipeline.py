from datetime import datetime, timezone
from pathlib import Path

from fpm.domain import ApprovalDecision
from fpm.pipeline import run_review
from fpm.store import JsonlRecordStore
from fpm.synthesize import FakeReviewSynthesizer

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)


def test_end_to_end_two_bundles(tmp_path):
    store = JsonlRecordStore(tmp_path)
    bundles = run_review(
        manifest_path="tests/fixtures/chainsafe.yaml",
        fixtures_dir=Path("fixtures/responses"),
        synthesizer=FakeReviewSynthesizer(),
        store=store,
        decide=lambda r: ApprovalDecision(action="approve", approver="carl"),
        as_of=AS_OF,
    )
    assert len(bundles) == 2
    by_fn = {b.recommendation.function_id: b for b in bundles}
    up = by_fn["network-uptime"].recommendation
    assert up.sla_outcome == "pass" and up.review_status == "meeting"
    assert up.versions.pipeline_version == "0.1.0"
    assert up.versions.measurement_window_end == AS_OF
    assert len(up.citations) == 1
    snap = by_fn["forest-snapshots"].recommendation
    assert snap.sla_outcome == "indeterminate" and snap.review_status == "pending_review"
    assert len(store.all_bundles()) == 2


def test_rejected_not_persisted(tmp_path):
    store = JsonlRecordStore(tmp_path)
    bundles = run_review(
        manifest_path="tests/fixtures/chainsafe.yaml",
        fixtures_dir=Path("fixtures/responses"),
        synthesizer=FakeReviewSynthesizer(),
        store=store,
        decide=lambda r: ApprovalDecision(action="reject", approver="carl"),
        as_of=AS_OF,
    )
    assert bundles == []
    assert store.all_bundles() == []
