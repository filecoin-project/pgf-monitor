"""Rebuilding Filecoin Pay settled volume from the settlement events behind it.

The nightly reads a running total with no time dimension, so the series would otherwise start the
day it was adopted. The settlements that produced that total carry `createdAt`, so the history is
recoverable — but only if the two genuinely agree, which is what most of these tests are about.
The failure being guarded against is the one that already happened once in this repo: a backfill
that computed a neighbouring quantity, under a name nothing joined to, for a year.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone

import pytest

UTC = timezone.utc


def _script():
    spec = importlib.util.spec_from_file_location("obs_pay", "scripts/observations.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["obs_pay"] = mod
    spec.loader.exec_module(mod)
    return mod


OBS = _script()
DAY = 86400
T0 = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())
USDFC = "0xusdfc"


def _fake_gql(settlements, running=None):
    """Stand in for the subgraph. `running` defaults to the true sum, i.e. a consistent source."""
    total = (
        running if running is not None else sum(int(s["totalSettledAmount"]) for s in settlements)
    )

    def gql(endpoint, query):
        if "tokens" in query and "settlements" not in query:
            return {
                "tokens": [
                    {
                        "id": USDFC,
                        "symbol": "USDFC",
                        "decimals": "18",
                        "totalSettledAmount": str(total),
                    }
                ]
            }
        after = None
        if "id_gt" in query:
            after = query.split('id_gt: "')[1].split('"')[0]
        page = [s for s in settlements if after is None or s["id"] > after]
        return {"settlements": page[:1000]}

    return gql


def _settle(idx: int, day: int, amount_eth: float):
    return {
        "id": f"{idx:04d}",
        "createdAt": str(T0 + day * DAY),
        "totalSettledAmount": str(int(amount_eth * 10**18)),
        "token": {"id": USDFC},
    }


def _run(monkeypatch, settlements, running=None, already=frozenset(), days=30):
    monkeypatch.setattr(OBS, "_gql", _fake_gql(settlements, running))
    monkeypatch.setattr(
        OBS, "filecoin_pay_target", lambda *a, **k: ("filoz", "fid", "met", "http://x", ["USDFC"])
    )
    now = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=days)
    return OBS._filecoin_pay_series(now - timedelta(days=400), now, set(already))


def test_the_series_is_cumulative_not_per_day(monkeypatch):
    rows = _run(monkeypatch, [_settle(1, 0, 10.0), _settle(2, 2, 5.0)], days=4)
    by_day = {r["observed_at"]: r["observed_value"] for r in rows}
    assert by_day["2026-01-01"] == pytest.approx(10.0)
    assert by_day["2026-01-02"] == pytest.approx(10.0)  # nothing settled, total holds
    assert by_day["2026-01-03"] == pytest.approx(15.0)  # second settlement lands
    assert by_day["2026-01-05"] == pytest.approx(15.0)


def test_it_refuses_to_write_when_the_reconstruction_is_not_the_nightlys_quantity(monkeypatch):
    """The whole point: if summing settlements does not reproduce the running total the nightly
    reads, the series would mean something different from its own present. Stop, do not write."""
    with pytest.raises(RuntimeError, match="NOT the nightly's quantity"):
        _run(monkeypatch, [_settle(1, 0, 10.0)], running=999 * 10**18)


def test_the_identity_check_passes_on_a_consistent_source(monkeypatch):
    rows = _run(monkeypatch, [_settle(1, 0, 3.0), _settle(2, 1, 4.0)], days=3)
    assert rows and rows[-1]["observed_value"] == pytest.approx(7.0)


def test_nothing_is_emitted_before_the_first_settlement(monkeypatch):
    """The true cumulative total is zero then, but a flat zero line reads as 'nobody is paying'
    rather than 'nothing is recorded'."""
    rows = _run(monkeypatch, [_settle(1, 10, 2.0)], days=12)
    assert min(r["observed_at"] for r in rows) == "2026-01-11"


def test_days_already_recorded_are_skipped(monkeypatch):
    already = {("2026-01-02", "filoz", "fid", "met")}
    rows = _run(monkeypatch, [_settle(1, 0, 1.0)], already=already, days=3)
    assert "2026-01-02" not in {r["observed_at"] for r in rows}
    assert len(rows) == 3


def test_rows_carry_the_registry_keys_and_a_distinct_method(monkeypatch):
    rows = _run(monkeypatch, [_settle(1, 0, 1.0)], days=1)
    r = rows[0]
    assert (r["team"], r["function_id"], r["metric"]) == ("filoz", "fid", "met")
    assert r["method"] == "backfill:api.goldsky.com"


def test_the_real_target_is_found_by_endpoint_and_matches_the_registry():
    """Located by its subgraph URL, not a hardcoded name, so a rename cannot orphan the rows."""
    import pathlib

    from fpm.manifest import load_manifest

    team, fid, metric, endpoint, symbols = OBS.filecoin_pay_target()
    assert OBS._FILPAY_SUBGRAPH_MARKER in endpoint
    assert set(symbols) == {"USDFC", "axlUSDC"}
    known = set()
    for p in sorted(pathlib.Path("registry").glob("*.yaml")):
        if p.name.startswith("_"):
            continue
        m = load_manifest(p)
        known |= {(m.team, f.function_id, f.sla.metric) for f in m.functions}
    assert (team, fid, metric) in known, "backfill would write rows joining to no commitment"


def test_filecoin_pay_is_not_in_the_default_rotation():
    assert "filecoin-pay" in OBS.TARGETED_ONLY
    assert "filecoin-pay" not in OBS.select_strategies(["releases", "filecoin-pay"], None)
