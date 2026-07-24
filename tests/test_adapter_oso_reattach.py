from datetime import datetime, timezone

from fpm.adapters.oso import OsoAdapter
from fpm.domain import window_for
from fpm.manifest import load_manifest
from fpm.oso.client import FakeOsoClient

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
ALLOW = {"api.drand.sh", "filfox.info"}


def _fn():
    return load_manifest("tests/fixtures/kernel_demo.yaml").functions[0]  # drand


def _W(fn):
    return window_for(fn.sla.cadence, AS_OF)


def test_reuses_dataset_when_config_unchanged():
    fn = _fn()
    client = FakeOsoClient(run_status="SUCCESS", query_rows=[{"expected": 5, "current": 5}])
    adapter = OsoAdapter(client, "org", ALLOW)
    adapter.fetch(fn, "kernel-demo", _W(fn))
    first = set(client._datasets)
    adapter.fetch(fn, "kernel-demo", _W(fn))
    assert set(client._datasets) == first  # same durable dataset reused


def test_recreates_dataset_when_config_changes():
    fn = _fn()
    client = FakeOsoClient(run_status="SUCCESS", query_rows=[{"expected": 5, "current": 5}])
    adapter = OsoAdapter(client, "org", ALLOW)
    adapter.fetch(fn, "kernel-demo", _W(fn))
    old = set(client._datasets)

    changed = _fn()
    changed.source.query = "/health-v2"  # source declaration changed
    adapter.fetch(changed, "kernel-demo", _W(changed))
    new = set(client._datasets)
    assert len(new) == 1 and new != old  # stale dataset deleted, recreated with fresh config


def test_get_config_roundtrips_on_fake():
    client = FakeOsoClient()
    ds = client.create_dataset("org", "d", "d")
    client.attach_rest_config(ds, {"client": {"base_url": "u"}})
    assert client.get_config(ds) == {"client": {"base_url": "u"}}
    client.delete_dataset(ds)
    assert client.get_config(ds) is None
