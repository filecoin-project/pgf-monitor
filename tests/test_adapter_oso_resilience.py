from datetime import datetime, timezone

from fpm.adapters.oso import OsoAdapter
from fpm.domain import window_for
from fpm.manifest import load_manifest
from fpm.oso.client import FakeOsoClient

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
ALLOW = {"api.drand.sh", "filfox.info"}


class FlakyPollClient(FakeOsoClient):
    """Raises on the first N get_runs calls (transient API errors), then behaves normally."""

    def __init__(self, fail_times: int, **kw):
        super().__init__(**kw)
        self._fails_left = fail_times

    def get_runs(self, dataset_id):
        if self._fails_left > 0:
            self._fails_left -= 1
            raise RuntimeError("502 Bad Gateway (transient)")
        return super().get_runs(dataset_id)


def test_poll_survives_transient_errors():
    fn = load_manifest("tests/fixtures/kernel_demo.yaml").functions[0]
    client = FlakyPollClient(
        fail_times=2, run_status="SUCCESS", query_rows=[{"expected": 5, "current": 5}]
    )
    adapter = OsoAdapter(client, "org", ALLOW, poll_attempts=5)
    reading = adapter.fetch(fn, "kernel-demo", window_for(fn.sla.cadence, AS_OF))
    assert reading.claim.value == 0.0  # transient poll errors absorbed, run still read
    assert reading.claim.evidence.oso_run_ref.status == "SUCCESS"


def test_persistent_poll_errors_yield_timeout():
    fn = load_manifest("tests/fixtures/kernel_demo.yaml").functions[0]
    client = FlakyPollClient(fail_times=99, run_status="SUCCESS", query_rows=[])
    adapter = OsoAdapter(client, "org", ALLOW, poll_attempts=3)
    reading = adapter.fetch(fn, "kernel-demo", window_for(fn.sla.cadence, AS_OF))
    assert reading.claim.value is None  # never confirmed -> value-less -> indeterminate
    assert reading.claim.evidence.oso_run_ref.status == "TIMEOUT"
