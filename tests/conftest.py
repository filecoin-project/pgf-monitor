# Shared fixtures go here when first needed. The package is importable via
# [tool.pytest.ini_options] pythonpath = ["src"] plus `uv sync`; no sys.path hacks.

from datetime import datetime, timezone

import pytest

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
from fpm.synthesize import SynthesisOutput

_WIN = MeasurementWindow(
    start=datetime(2026, 6, 1, tzinfo=timezone.utc), end=datetime(2026, 7, 1, tzinfo=timezone.utc)
)


def _make_bundle(
    rid="rec-1", narrative="model says: ok, all good", note="looks fine", approver="carl"
):
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
                canonical_payload_hash="a" * 64,
                request_fingerprint="b" * 64,
                evidence_bundle_hash="c" * 64,
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


@pytest.fixture
def sample_bundle():
    return _make_bundle
