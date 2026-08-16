from datetime import datetime, timezone
from pathlib import Path

import pytest

from fpm.adapters.registry import build_adapters
from fpm.detectors.base import DETECTORS
from fpm.domain import window_for
from fpm.dossier import assemble_dossier
from fpm.evaluate import evaluate_sla
from fpm.gate import GateError, validate_recommendation
from fpm.manifest import load_manifest
from fpm.synthesize import SynthesisOutput

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
H = "b" * 64


def _dossier(idx):
    m = load_manifest("tests/fixtures/chainsafe.yaml")
    fn = m.functions[idx]
    reading = build_adapters(Path("fixtures/responses"))["fixture"].fetch(
        fn, "chainsafe", window_for(fn.sla.cadence, AS_OF)
    )
    sla = evaluate_sla(reading, fn, "chainsafe")
    results = DETECTORS.results(reading, fn)
    return assemble_dossier(m, fn, reading, sla, results, DETECTORS.flags(results))


def test_valid_recommendation_passes():
    d = _dossier(0)
    out = SynthesisOutput(
        review_status="meeting",
        narrative="ok",
        cited_evidence_hashes=[d.reading.claim.evidence.evidence_bundle_hash],
    )
    validate_recommendation(out, d)


def test_unknown_evidence_hash_rejected():
    d = _dossier(0)
    out = SynthesisOutput(review_status="meeting", narrative="ok", cited_evidence_hashes=[H])
    with pytest.raises(GateError):
        validate_recommendation(out, d)


def test_indeterminate_cannot_be_breach():
    d = _dossier(1)
    out = SynthesisOutput(review_status="breach", narrative="x", cited_evidence_hashes=[])
    with pytest.raises(GateError):
        validate_recommendation(out, d)


def test_unscored_cannot_be_meeting():
    d = _dossier(0)
    d = d.model_copy(update={"sla_result": d.sla_result.model_copy(update={"outcome": "unscored"})})
    out = SynthesisOutput(review_status="meeting", narrative="x", cited_evidence_hashes=[])
    with pytest.raises(GateError):
        validate_recommendation(out, d)


def test_unscored_cannot_be_breach():
    d = _dossier(0)
    d = d.model_copy(update={"sla_result": d.sla_result.model_copy(update={"outcome": "unscored"})})
    out = SynthesisOutput(review_status="breach", narrative="x", cited_evidence_hashes=[])
    with pytest.raises(GateError):
        validate_recommendation(out, d)


def test_blank_narrative_rejected():
    d = _dossier(0)
    out = SynthesisOutput(
        review_status="meeting",
        narrative="  ",
        cited_evidence_hashes=[d.reading.claim.evidence.evidence_bundle_hash],
    )
    with pytest.raises(GateError):
        validate_recommendation(out, d)
