from datetime import datetime, timezone
from pathlib import Path

from fpm.adapters.registry import build_adapters
from fpm.detectors.base import DETECTORS
from fpm.detectors.window import WindowDetector
from fpm.domain import window_for
from fpm.manifest import load_manifest

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _read(idx):
    fn = load_manifest("tests/fixtures/chainsafe.yaml").functions[idx]
    r = build_adapters(Path("fixtures/responses"))["fixture"].fetch(
        fn, "chainsafe", window_for(fn.sla.cadence, AS_OF)
    )
    return r, fn


def test_no_signal_when_window_matches_cadence():
    reading, fn = _read(0)  # declared 30d, monthly cadence -> 30 days
    assert WindowDetector().run(reading, fn).signal == "no_signal"


def test_signal_when_window_mismatch():
    reading, fn = _read(0)
    reading.source_metadata["declared_window_days"] = 7  # not monthly
    assert WindowDetector().run(reading, fn).signal == "signal_detected"


def test_insufficient_data_when_no_window_metadata():
    reading, fn = _read(0)
    reading.source_metadata.pop("declared_window_days")
    assert WindowDetector().run(reading, fn).signal == "insufficient_data"


def test_not_applicable_to_other_metric():
    reading, fn = _read(1)
    assert WindowDetector().run(reading, fn).signal == "not_applicable"


def test_registry_keeps_all_results_but_flags_only_signal_detected():
    reading, fn = _read(0)
    reading.source_metadata["declared_window_days"] = 7
    results = DETECTORS.results(reading, fn)
    assert any(r.signal == "signal_detected" for r in results)
    flags = DETECTORS.flags(results)
    assert len(flags) == 1 and flags[0].detector_id == "window-vs-cadence"
