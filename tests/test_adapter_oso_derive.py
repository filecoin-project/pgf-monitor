from datetime import datetime, timezone

from fpm.adapters.oso import OsoAdapter
from fpm.domain import window_for
from fpm.evaluate import evaluate_sla
from fpm.manifest import load_manifest
from fpm.oso.client import FakeOsoClient

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
ALLOW = {"api.drand.sh", "filfox.info"}


def _fn(idx):
    return load_manifest("tests/fixtures/kernel_demo.yaml").functions[idx]


def test_drand_diff_in_sync_passes():
    fn = _fn(0)  # randomness-beacon, derive=diff (expected - current)
    client = FakeOsoClient(
        run_status="SUCCESS", query_rows=[{"expected": 6279615, "current": 6279615}]
    )
    reading = OsoAdapter(client, "org", ALLOW).fetch(
        fn, "kernel-demo", window_for(fn.sla.cadence, AS_OF)
    )
    assert reading.claim.value == 0.0  # in sync
    assert reading.metric == "beacon_round_lag"
    assert evaluate_sla(reading, fn, "kernel-demo").outcome == "pass"


def test_drand_diff_lagging_fails():
    fn = _fn(0)
    client = FakeOsoClient(
        run_status="SUCCESS", query_rows=[{"expected": 6279620, "current": 6279615}]
    )
    reading = OsoAdapter(client, "org", ALLOW).fetch(
        fn, "kernel-demo", window_for(fn.sla.cadence, AS_OF)
    )
    assert reading.claim.value == 5.0
    assert evaluate_sla(reading, fn, "kernel-demo").outcome == "fail"
