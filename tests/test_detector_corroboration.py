from datetime import datetime, timezone

from fpm.adapters.oso import OsoAdapter
from fpm.detectors.corroboration import CorroborationDetector, build_detectors
from fpm.domain import window_for
from fpm.manifest import load_manifest
from fpm.oso.client import FakeOsoClient

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
ALLOW = {"api.llama.fi"}


def _reading(tvl_rows):
    fn = load_manifest("tests/fixtures/chainsafe_oso.yaml").functions[0]
    client = FakeOsoClient(run_status="SUCCESS", query_rows=tvl_rows)
    reading = OsoAdapter(client, "org", ALLOW).fetch(
        fn, "chainsafe", window_for(fn.sla.cadence, AS_OF)
    )
    return reading, fn


def test_no_signal_when_corroborates():
    reading, fn = _reading([{"date": 1, "tvl": 1_000_000}])
    det = CorroborationDetector(FakeOsoClient(query_rows=[{"v": 1_020_000}]), "SELECT 1", "v")
    assert det.run(reading, fn).signal == "no_signal"


def test_signal_when_diverges():
    reading, fn = _reading([{"date": 1, "tvl": 1_000_000}])
    det = CorroborationDetector(FakeOsoClient(query_rows=[{"v": 5_000_000}]), "SELECT 1", "v")
    assert det.run(reading, fn).signal == "signal_detected"


def test_insufficient_when_no_corroborating_row():
    reading, fn = _reading([{"date": 1, "tvl": 1_000_000}])
    det = CorroborationDetector(FakeOsoClient(query_rows=[]), "SELECT 1", "v")
    assert det.run(reading, fn).signal == "insufficient_data"


def test_build_detectors_adds_corroboration_only_with_client():
    assert len(build_detectors()._detectors) == 1
    assert len(build_detectors(FakeOsoClient())._detectors) == 2


def test_registry_isolates_raising_detector():
    # A detector that raises (missing corroboration table, network error) must not
    # abort the review — it degrades to insufficient_data with the error in the note.
    class _Boom:
        contract = CorroborationDetector.contract

        def run(self, reading, fn):
            raise RuntimeError("TABLE_NOT_FOUND: oso.filecoin_tvl_independent")

    from fpm.detectors.base import DetectorRegistry

    reading, fn = _reading([{"date": 1, "tvl": 1_000_000}])
    results = DetectorRegistry([_Boom()]).results(reading, fn)
    assert len(results) == 1
    assert results[0].signal == "insufficient_data"
    assert "TABLE_NOT_FOUND" in results[0].note
