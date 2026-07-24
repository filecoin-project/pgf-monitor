from datetime import datetime, timezone
from pathlib import Path

from fpm.domain import (
    ApprovalDecision,
    Citation,
    MeasurementWindow,
    ReviewRecommendation,
    VersionSet,
)
from fpm.dossier import ReviewDossier
from fpm.store import JsonlRecordStore, human_adjudicate
from fpm.synthesize import SynthesisOutput

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
H = "c" * 64


def _rec():
    return ReviewRecommendation(
        recommendation_id="chainsafe:network-uptime:2026-07-01:deadbeef",
        team="chainsafe",
        function_id="network-uptime",
        review_status="meeting",
        sla_outcome="pass",
        narrative="ok",
        citations=[Citation(evidence_bundle_hash=H, source_ref="grafana://forest/uptime")],
        flags=[],
        detector_results=[],
        versions=VersionSet(
            manifest_commit_sha="deadbeef",
            commitment_version="1",
            measurement_window_start=AS_OF,
            measurement_window_end=AS_OF,
            adapter_version="0.1.0",
            pipeline_version="0.1.0",
            rubric_version="0.1.0",
            detector_versions={"window-vs-cadence": "0.1.0"},
            model_id="fake",
            prompt_version="0",
        ),
    )


def _dossier_stub(rec):
    from fpm.domain import Claim, EvidenceRef, Reading, SlaResult

    ev = EvidenceRef(
        raw_payload_hash=H,
        canonical_payload_hash=H,
        request_fingerprint=H,
        evidence_bundle_hash=H,
    )
    win = MeasurementWindow(start=AS_OF, end=AS_OF)
    reading = Reading(
        team="chainsafe",
        function_id="network-uptime",
        metric="uptime_ratio",
        measurement_window=win,
        claim=Claim(
            value=0.999,
            origin="independent",
            source_ref="s",
            fetched_at=AS_OF,
            evidence=ev,
            fetched_by="f",
        ),
        adapter="fixture",
        adapter_version="0.1.0",
    )
    sla = SlaResult(
        outcome="pass",
        op=">=",
        threshold=0.999,
        observed=0.999,
        measurement_window=win,
        reason="ok",
    )
    return ReviewDossier(
        team="chainsafe",
        function_id="network-uptime",
        sla_statement="s",
        sla_result=sla,
        reading=reading,
        detector_results=[],
        flags=[],
        context=[],
    )


def test_approve_produces_bundle_sharing_id():
    rec = _rec()
    out = SynthesisOutput(review_status="meeting", narrative="ok", cited_evidence_hashes=[H])
    bundle = human_adjudicate(
        rec,
        _dossier_stub(rec),
        out,
        decide=lambda r: ApprovalDecision(action="approve", approver="carl"),
    )
    assert bundle is not None
    assert bundle.verdict.recommendation_id == rec.recommendation_id
    assert bundle.verdict.approver == "carl"
    assert bundle.verdict.adjudicated_status == "meeting"


def test_revise_changes_status():
    rec = _rec()
    out = SynthesisOutput(review_status="meeting", narrative="ok", cited_evidence_hashes=[H])
    bundle = human_adjudicate(
        rec,
        _dossier_stub(rec),
        out,
        decide=lambda r: ApprovalDecision(
            action="revise", approver="carl", adjudicated_status="at-risk", note="context"
        ),
    )
    assert bundle.verdict.adjudicated_status == "at-risk"
    assert bundle.verdict.action == "revise"


def test_reject_returns_none():
    rec = _rec()
    out = SynthesisOutput(review_status="meeting", narrative="ok", cited_evidence_hashes=[H])
    assert (
        human_adjudicate(
            rec,
            _dossier_stub(rec),
            out,
            decide=lambda r: ApprovalDecision(action="reject", approver="carl"),
        )
        is None
    )


def test_store_roundtrips_one_bundle(tmp_path: Path):
    rec = _rec()
    out = SynthesisOutput(review_status="meeting", narrative="ok", cited_evidence_hashes=[H])
    bundle = human_adjudicate(
        rec,
        _dossier_stub(rec),
        out,
        decide=lambda r: ApprovalDecision(action="approve", approver="carl"),
    )
    store = JsonlRecordStore(tmp_path)
    store.save_adjudication(bundle)
    loaded = store.all_bundles()
    assert len(loaded) == 1
    assert loaded[0].recommendation.recommendation_id == rec.recommendation_id
    assert loaded[0].verdict.recommendation_id == rec.recommendation_id
