from datetime import datetime, timezone
from pathlib import Path

from fpm.adapters.registry import build_adapters
from fpm.detectors.base import DETECTORS
from fpm.domain import window_for
from fpm.dossier import assemble_dossier, retrieve_context
from fpm.evaluate import evaluate_sla
from fpm.manifest import load_manifest

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)


def test_assemble_bundles_computed_facts():
    m = load_manifest("tests/fixtures/chainsafe.yaml")
    fn = m.functions[0]
    reading = build_adapters(Path("fixtures/responses"))["fixture"].fetch(
        fn, "chainsafe", window_for(fn.sla.cadence, AS_OF)
    )
    sla = evaluate_sla(reading, fn, "chainsafe")
    results = DETECTORS.results(reading, fn)
    d = assemble_dossier(m, fn, reading, sla, results, DETECTORS.flags(results))
    assert d.sla_result.outcome == "pass"
    assert d.reading.claim.origin == "independent"
    assert any(r.detector_id == "window-vs-cadence" for r in d.detector_results)
    assert d.context == []


def test_context_stub_empty():
    assert retrieve_context("chainsafe", "network-uptime") == []
