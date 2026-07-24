from datetime import datetime, timezone

from fpm.adapters.oso import OsoAdapter
from fpm.domain import window_for
from fpm.evaluate import evaluate_sla
from fpm.manifest import load_manifest
from fpm.oso.client import FakeOsoClient

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
ALLOW = {"api.llama.fi"}


def _fn():
    return load_manifest("tests/fixtures/chainsafe_oso.yaml").functions[0]


def _rows():
    return [
        {"date": 100, "tvl": 3_000_000, "_dlt_load_id": "L", "_dlt_id": "a"},
        {"date": 300, "tvl": 3_900_000, "_dlt_load_id": "L", "_dlt_id": "b"},
        {"date": 200, "tvl": 3_500_000, "_dlt_load_id": "L", "_dlt_id": "c"},
    ]


def test_success_reduces_latest_and_attaches_provenance():
    fn = _fn()
    client = FakeOsoClient(run_status="SUCCESS", query_rows=_rows())
    adapter = OsoAdapter(client, org_id="org", allowlist=ALLOW)
    reading = adapter.fetch(fn, "chainsafe", window_for(fn.sla.cadence, AS_OF))
    assert reading.claim.value == 3_900_000.0  # latest by date
    assert reading.claim.origin == "independent"
    assert reading.claim.evidence is not None
    assert reading.claim.evidence.raw_payload_hash is None
    assert reading.claim.evidence.oso_run_ref.status == "SUCCESS"
    assert evaluate_sla(reading, fn, "chainsafe").outcome == "pass"


def test_reuses_existing_dataset():
    fn = _fn()
    client = FakeOsoClient(run_status="SUCCESS", query_rows=_rows())
    adapter = OsoAdapter(client, org_id="org", allowlist=ALLOW)
    adapter.fetch(fn, "chainsafe", window_for(fn.sla.cadence, AS_OF))
    adapter.fetch(fn, "chainsafe", window_for(fn.sla.cadence, AS_OF))
    assert len(client._datasets) == 1  # durable dataset reused, not recreated


def test_failed_run_yields_indeterminate():
    fn = _fn()
    client = FakeOsoClient(run_status="FAILED")
    adapter = OsoAdapter(client, org_id="org", allowlist=ALLOW)
    reading = adapter.fetch(fn, "chainsafe", window_for(fn.sla.cadence, AS_OF))
    assert reading.claim.value is None
    assert reading.claim.evidence.oso_run_ref.status == "FAILED"
    assert evaluate_sla(reading, fn, "chainsafe").outcome == "indeterminate"


def test_timeout_yields_indeterminate():
    fn = _fn()
    client = FakeOsoClient(run_status="RUNNING")  # never terminal
    adapter = OsoAdapter(client, org_id="org", allowlist=ALLOW, poll_attempts=2)
    reading = adapter.fetch(fn, "chainsafe", window_for(fn.sla.cadence, AS_OF))
    assert reading.claim.value is None
    assert evaluate_sla(reading, fn, "chainsafe").outcome == "indeterminate"


def test_fetch_retries_empty_read_until_rows_materialize():
    # A run can report SUCCESS before the Iceberg table is queryable; the first read
    # sees 0 rows (or raises). With poll_sleep set, fetch retries instead of emitting
    # a phantom indeterminate. (Found live 2026-07-15: dns.google + filfox flakes.)
    fn = load_manifest("tests/fixtures/chainsafe_oso.yaml").functions[0]
    client = FakeOsoClient(run_status="SUCCESS", query_rows=[{"date": 1, "tvl": 2_000_000}])
    calls = {"n": 0}
    real_query = client.query

    def _lagging_query(sql):
        calls["n"] += 1
        if calls["n"] <= 2:
            return []
        return real_query(sql)

    client.query = _lagging_query
    adapter = OsoAdapter(client, "org", ALLOW, poll_sleep=0.01)
    reading = adapter.fetch(fn, "chainsafe", window_for(fn.sla.cadence, AS_OF))
    assert reading.claim.value == 2_000_000.0


def test_fetch_no_retry_without_poll_sleep():
    fn = load_manifest("tests/fixtures/chainsafe_oso.yaml").functions[0]
    client = FakeOsoClient(run_status="SUCCESS", query_rows=[{"date": 1, "tvl": 2_000_000}])
    client.query = lambda sql: []
    adapter = OsoAdapter(client, "org", ALLOW, poll_sleep=0.0)
    reading = adapter.fetch(fn, "chainsafe", window_for(fn.sla.cadence, AS_OF))
    assert reading.claim.value is None
