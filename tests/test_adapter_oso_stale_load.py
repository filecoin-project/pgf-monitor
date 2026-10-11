"""A SUCCESS run over rows an earlier run fetched must not become tonight's reading.

When an OSO ingestion run fails at dlt's load step, its package stays pending, and the next run on
that dataset loads it and drops its own fetch. That run still reports SUCCESS, so the reading
would land under tonight's date carrying last night's number. Seen live on fil-b and goldsky
datasets in October 2026. It is invisible in the CSV: the value is plausible, just a day old.

Every row dlt writes carries `_dlt_load_id`, the epoch second its load began. Rows loaded well
before the run was triggered are refused: no value, a `stale_load` note, and a retry, because the
stale run consumed the pending package and the next run fetches fresh.
"""

import time
from datetime import datetime, timezone

import pytest

from fpm.adapters.oso import OsoAdapter
from fpm.domain import window_for
from fpm.manifest import load_manifest
from fpm.observe import retryable
from fpm.oso.client import FakeOsoClient

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
ALLOW = {"api.drand.sh", "filfox.info"}
HOUR = 3600.0


def _fetch(rows):
    fn = load_manifest("tests/fixtures/kernel_demo.yaml").functions[0]
    client = FakeOsoClient(run_status="SUCCESS", query_rows=rows)
    adapter = OsoAdapter(client, "org", ALLOW)
    return adapter.fetch(fn, "kernel-demo", window_for(fn.sla.cadence, AS_OF))


def _rows(loaded_ago: float):
    return [{"expected": 5, "current": 5, "_dlt_load_id": f"{time.time() - loaded_ago:.6f}"}]


def test_rows_from_a_night_earlier_are_refused():
    reading = _fetch(_rows(loaded_ago=24 * HOUR))
    assert reading.claim.value is None
    assert "pending" in reading.source_metadata["stale_load"]
    assert reading.raw_rows  # kept as evidence of what was loaded
    assert retryable(reading)


def test_rows_this_run_loaded_are_read():
    reading = _fetch(_rows(loaded_ago=-5.0))  # dlt's load starts after the trigger
    assert reading.claim.value == 0.0
    assert "stale_load" not in reading.source_metadata
    assert not retryable(reading)


def test_a_same_night_retry_may_read_its_first_attempts_package():
    """A retry runs at the end of the night, after its first attempt failed at the load step
    and left that package pending. Those rows were fetched tonight; refusing them would turn a
    recoverable night into a lost one."""
    reading = _fetch(_rows(loaded_ago=40 * 60))
    assert reading.claim.value == 0.0


def test_the_newest_load_decides():
    """Ingestion tables are `write_disposition: replace`, so one load fills the table and the max
    is that load. Pinned anyway in case a table ever holds several: the newest decides. That
    proves only that the newest load is current, not that every row is."""
    rows = _rows(loaded_ago=48 * HOUR) + _rows(loaded_ago=-5.0)
    assert "stale_load" not in _fetch(rows).source_metadata


@pytest.mark.parametrize("load_id", [None, "", "not-a-number"])
def test_rows_without_a_usable_load_id_are_not_judged(load_id):
    rows = [{"expected": 5, "current": 5, "_dlt_load_id": load_id}]
    assert _fetch(rows).claim.value == 0.0
    assert _fetch([{"expected": 5, "current": 5}]).claim.value == 0.0


def test_the_check_runs_before_a_transform():
    """The transform reads the same raw table, so stale rows would feed it a stale number."""
    from tests.test_adapter_oso_transform import ALLOW as TRANSFORM_ALLOW
    from tests.test_adapter_oso_transform import _transform_fn

    fn = _transform_fn()
    rows = [{"m": 480.0, "_dlt_load_id": f"{time.time() - 24 * HOUR:.6f}"}]
    client = FakeOsoClient(run_status="SUCCESS", query_rows=rows)
    adapter = OsoAdapter(client, "org", TRANSFORM_ALLOW)
    reading = adapter.fetch(fn, "team", window_for(fn.sla.cadence, AS_OF))
    assert reading.claim.value is None
    assert "stale_load" in reading.source_metadata
    assert "transform_error" not in reading.source_metadata


# ------------------------------------------------- lags and ages measure from the load


def _capture_now(monkeypatch, name):
    """Record the `now` the adapter hands to bind_transform_sql or derive_observed."""
    import fpm.adapters.oso as oso_mod

    seen = []
    real = getattr(oso_mod, name)

    def spy(*args):
        seen.append(args[-1])
        return real(*args)

    monkeypatch.setattr(oso_mod, name, spy)
    return seen


def test_a_transform_measures_from_when_the_rows_were_loaded(monkeypatch):
    """2026-10-11: a retry loaded rows its first attempt fetched 8 minutes earlier, and
    `now - newest block` counted those 8 minutes as goldsky indexing lag (532s, true ~34s)."""
    from tests.test_adapter_oso_transform import ALLOW as TRANSFORM_ALLOW
    from tests.test_adapter_oso_transform import _transform_fn

    seen = _capture_now(monkeypatch, "bind_transform_sql")
    loaded = time.time() - 8 * 60
    rows = [{"m": 480.0, "_dlt_load_id": f"{loaded:.6f}"}]
    adapter = OsoAdapter(
        FakeOsoClient(run_status="SUCCESS", query_rows=rows), "org", TRANSFORM_ALLOW
    )
    fn = _transform_fn()
    adapter.fetch(fn, "team", window_for(fn.sla.cadence, AS_OF))

    assert seen == [datetime.fromtimestamp(loaded, timezone.utc)]


def test_an_age_derive_measures_from_when_the_rows_were_loaded(monkeypatch):
    seen = _capture_now(monkeypatch, "derive_observed")
    loaded = time.time() - 8 * 60
    _fetch([{"expected": 5, "current": 5, "_dlt_load_id": f"{loaded:.6f}"}])
    assert seen == [datetime.fromtimestamp(loaded, timezone.utc)]


def test_without_a_load_id_the_fetch_time_stands_in(monkeypatch):
    seen = _capture_now(monkeypatch, "derive_observed")
    before = datetime.now(timezone.utc)
    _fetch([{"expected": 5, "current": 5}])
    assert before <= seen[0] <= datetime.now(timezone.utc)
