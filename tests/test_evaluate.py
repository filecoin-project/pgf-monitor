from datetime import datetime, timezone
from pathlib import Path

from fpm.adapters.registry import build_adapters
from fpm.domain import Reading, window_for
from fpm.evaluate import evaluate_sla
from fpm.manifest import load_manifest

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _read(idx):
    fn = load_manifest("tests/fixtures/chainsafe.yaml").functions[idx]
    reading = build_adapters(Path("fixtures/responses"))["fixture"].fetch(
        fn, "chainsafe", window_for(fn.sla.cadence, AS_OF)
    )
    return reading, fn


def test_pass_when_met():
    reading, fn = _read(0)
    assert evaluate_sla(reading, fn, "chainsafe").outcome == "pass"


def test_indeterminate_when_value_missing():
    reading, fn = _read(1)
    assert evaluate_sla(reading, fn, "chainsafe").outcome == "indeterminate"


def test_indeterminate_when_not_independent():
    reading, fn = _read(0)
    t = reading.model_copy(deep=True)
    t.claim.origin = "asserted"
    r = evaluate_sla(Reading.model_validate(t.model_dump()), fn, "chainsafe")
    assert r.outcome == "indeterminate" and "independent" in r.reason


def test_indeterminate_when_evidence_missing():
    reading, fn = _read(0)
    t = reading.model_copy(deep=True)
    t.claim.evidence = None
    r = evaluate_sla(Reading.model_validate(t.model_dump()), fn, "chainsafe")
    assert r.outcome == "indeterminate" and "provenance" in r.reason


def test_indeterminate_on_metric_mismatch():
    reading, fn = _read(0)
    t = reading.model_copy(deep=True)
    t.metric = "something-else"
    r = evaluate_sla(Reading.model_validate(t.model_dump()), fn, "chainsafe")
    assert r.outcome == "indeterminate" and "metric" in r.reason


def test_indeterminate_on_team_mismatch():
    reading, fn = _read(0)
    r = evaluate_sla(reading, fn, "someone-else")
    assert r.outcome == "indeterminate" and "team" in r.reason


def test_fail_when_below():
    reading, fn = _read(0)
    t = reading.model_copy(deep=True)
    t.claim.value = 0.5
    assert evaluate_sla(Reading.model_validate(t.model_dump()), fn, "chainsafe").outcome == "fail"
