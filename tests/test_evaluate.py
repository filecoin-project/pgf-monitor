from datetime import datetime, timezone
from pathlib import Path

import pytest

from fpm.adapters.registry import build_adapters
from fpm.domain import Reading, window_for
from fpm.evaluate import evaluate_sla, meets_threshold
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


@pytest.mark.parametrize(
    "value,op,threshold,expected",
    [
        (0.90, ">=", 0.90, True),   # boundary equality passes for >=
        (0.89, ">=", 0.90, False),
        (0.90, ">", 0.90, False),   # boundary equality fails for >
        (0.91, ">", 0.90, True),
        (5.0, "<=", 5.0, True),
        (5.1, "<=", 5.0, False),
        (5.0, "<", 5.0, False),
        (4.9, "<", 5.0, True),
        (3.0, "==", 3.0, True),
        (3.1, "==", 3.0, False),
    ],
)
def test_meets_threshold_across_every_operator(value, op, threshold, expected):
    assert meets_threshold(value, op, threshold) is expected


def test_no_threshold_yields_unscored_with_the_value_preserved():
    """A function with no agreed SLA is measured, not judged.

    The value must survive — 'unscored' says nobody committed to a bar, NOT that the
    measurement failed. That is what distinguishes it from 'indeterminate'.
    """
    reading, fn = _read(0)
    fn.sla.threshold_op = None
    fn.sla.threshold_value = None
    result = evaluate_sla(reading, fn, "chainsafe")
    assert result.outcome == "unscored"
    assert result.observed == reading.claim.value
    assert result.threshold is None
    assert "not scored" in result.reason


def test_a_reading_with_no_value_is_indeterminate_even_without_a_threshold():
    """Admissibility is checked BEFORE the threshold. No value means indeterminate,
    never unscored — otherwise a dead source would silently look like an unbound metric.
    """
    reading, fn = _read(1)
    fn.sla.threshold_op = None
    fn.sla.threshold_value = None
    assert evaluate_sla(reading, fn, "chainsafe").outcome == "indeterminate"
