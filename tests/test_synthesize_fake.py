from datetime import datetime, timezone
from pathlib import Path

from fpm.adapters.registry import build_adapters
from fpm.detectors.base import DETECTORS
from fpm.domain import window_for
from fpm.dossier import assemble_dossier
from fpm.evaluate import evaluate_sla
from fpm.manifest import load_manifest
from fpm.synthesize import SYNTHESIS_JSON_SCHEMA, FakeReviewSynthesizer

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _dossier(idx):
    m = load_manifest("tests/fixtures/chainsafe.yaml")
    fn = m.functions[idx]
    reading = build_adapters(Path("fixtures/responses"))["fixture"].fetch(
        fn, "chainsafe", window_for(fn.sla.cadence, AS_OF)
    )
    sla = evaluate_sla(reading, fn, "chainsafe")
    results = DETECTORS.results(reading, fn)
    return assemble_dossier(m, fn, reading, sla, results, DETECTORS.flags(results))


def test_fake_pass_meeting_cites_evidence_hash():
    d = _dossier(0)
    out = FakeReviewSynthesizer().synthesize(d)
    assert out.review_status == "meeting"
    assert out.cited_evidence_hashes == [d.reading.claim.evidence.evidence_bundle_hash]


def test_fake_indeterminate_pending_no_citation():
    out = FakeReviewSynthesizer().synthesize(_dossier(1))
    assert out.review_status == "pending_review"
    assert out.cited_evidence_hashes == []


def test_fake_exposes_metadata():
    s = FakeReviewSynthesizer()
    assert s.model_id == "fake" and s.prompt_version == "0"


def test_schema_fields():
    assert set(SYNTHESIS_JSON_SCHEMA["properties"]) >= {
        "review_status",
        "narrative",
        "cited_evidence_hashes",
        "flag_notes",
    }
