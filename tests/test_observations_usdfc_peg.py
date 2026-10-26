"""Re-reading the USDFC peg from the pool contract at a past block.

GeckoTerminal froze every USDFC pool at 2026-10-13 10:00 UTC and served the same price for a week.
The registry now reads slot0() on chain, and the backfill replays that read at each night's block.
It is only worth anything if it computes exactly what the registry's transform computes, so the
tests pin the Python decode to the SQL and refuse to run when the registry drifts from it.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from datetime import datetime, timedelta, timezone

import pytest

UTC = timezone.utc


def _script():
    spec = importlib.util.spec_from_file_location("obs_peg", "scripts/observations.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["obs_peg"] = mod
    spec.loader.exec_module(mod)
    return mod


OBS = _script()
NOW = datetime(2026, 10, 26, 17, 0, tzinfo=UTC)

# slot0() on the USDFC/axlUSDC pool, read live on 2026-10-26 (word 0 is sqrtPriceX96).
SLOT0 = (
    "0x0000000000000000000000000000000000000000000010bab3caf63e57818730"
    "fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffbc862"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000001"
    "0000000000000000000000000000000000000000000000000000000000000001"
    "0000000000000000000000000000000000000000000000000000000000000044"
    "0000000000000000000000000000000000000000000000000000000000000001"
)


def test_the_chunked_decode_equals_the_exact_price():
    exact = (int(SLOT0[2:66], 16) / 2**96) ** 2 * 1e12 - 1
    assert OBS.peg_deviation_from_slot0(SLOT0) == pytest.approx(exact, abs=1e-12)
    assert OBS.peg_deviation_from_slot0(SLOT0) == pytest.approx(-0.0057, abs=1e-4)


def test_the_registry_reads_exactly_what_the_backfill_replays():
    team, fid, metric, endpoint, pool = OBS.usdfc_peg_target()
    assert (team, fid, metric) == ("secured-finance", "usdfc-peg-deviation", "usdfc_peg_deviation")
    assert endpoint == "https://filecoin.chain.love/rpc/v1"
    assert pool == "0x21ca72fe39095db9642ca9cc694fa056f906037f"


def test_it_refuses_a_registry_whose_transform_has_drifted(tmp_path):
    shutil.copy("registry/secured-finance.yaml", tmp_path / "secured-finance.yaml")
    path = tmp_path / "secured-finance.yaml"
    path.write_text(path.read_text().replace("* 1e12) - 1 FROM raw", "* 1e12) FROM raw"))
    with pytest.raises(ValueError, match="Reconcile"):
        OBS.usdfc_peg_target(str(tmp_path))


def _run(monkeypatch, read, have_value=frozenset(), days=3):
    monkeypatch.setattr(
        OBS,
        "usdfc_peg_target",
        lambda *a, **k: (
            "secured-finance",
            "fid",
            "met",
            "https://filecoin.chain.love/rpc/v1",
            "0xp",
        ),
    )
    return OBS._usdfc_peg_series(NOW - timedelta(days=days), NOW, set(have_value), read=read)


def test_each_night_is_read_at_its_own_read_instant(monkeypatch):
    asked = []

    def read(block):
        asked.append(block)
        return SLOT0

    rows = _run(monkeypatch, read)
    assert [r["observed_at"] for r in rows] == [
        "2026-10-23",
        "2026-10-24",
        "2026-10-25",
        "2026-10-26",
    ]
    assert asked == [
        OBS.epoch_at(OBS._anchor(datetime(2026, 10, d, tzinfo=UTC))) for d in range(23, 27)
    ]
    assert {r["method"] for r in rows} == {"backfill:filecoin.chain.love"}


def test_days_that_already_carry_a_value_are_left_alone(monkeypatch):
    rows = _run(
        monkeypatch, lambda b: SLOT0, have_value={("2026-10-24", "secured-finance", "fid", "met")}
    )
    assert "2026-10-24" not in {r["observed_at"] for r in rows}


def test_days_past_the_node_lookback_are_skipped_not_invented(monkeypatch):
    oldest = OBS.epoch_at(OBS._anchor(datetime(2026, 10, 25, tzinfo=UTC)))

    def read(block):
        if block < oldest:
            raise OBS.LookbackExceeded("lookbacks of more than 336h0m0s are disallowed")
        return SLOT0

    rows = _run(monkeypatch, read)
    assert [r["observed_at"] for r in rows] == ["2026-10-25", "2026-10-26"]


def test_the_chain_strategies_are_not_in_the_default_rotation():
    assert {"usdfc-peg", "usdfc-pool"} <= OBS.TARGETED_ONLY


# --- pool depth and volume ------------------------------------------------------------------------


class _FakeChain:
    def __init__(self, oldest_block=0):
        self.oldest, self.asked = oldest_block, []

    def _check(self, block):
        self.asked.append(block)
        if block < self.oldest:
            raise OBS.LookbackExceeded("lookbacks of more than 336h0m0s are disallowed")

    def depth(self, block):
        self._check(block)
        return 21_000.0

    def volume(self, block):
        self._check(block)
        return 9_000.0


def _pool_run(chain, have_value=frozenset(), days=1):
    return OBS._usdfc_pool_series(NOW - timedelta(days=days), NOW, set(have_value), chain=chain)


def test_the_registry_pool_metrics_read_the_peg_pool():
    targets = OBS.usdfc_pool_targets("0x21ca72fe39095db9642ca9cc694fa056f906037f")
    assert targets == {
        "usdfc_pool_tvl_usd": ("secured-finance", "usdfc-axlusdc-pool-tvl"),
        "usdfc_pool_volume_usd": ("secured-finance", "usdfc-axlusdc-pool-volume"),
    }


def test_it_refuses_pool_metrics_pointed_at_another_pool():
    with pytest.raises(ValueError, match="Reconcile"):
        OBS.usdfc_pool_targets("0x0000000000000000000000000000000000000001")


def test_both_pool_metrics_are_rebuilt_per_night_and_valued_days_are_skipped():
    have = {("2026-10-26", "secured-finance", "usdfc-axlusdc-pool-tvl", "usdfc_pool_tvl_usd")}
    rows = _pool_run(_FakeChain(), have_value=have)
    got = {(r["observed_at"], r["metric"]): r for r in rows}
    assert set(got) == {
        ("2026-10-25", "usdfc_pool_tvl_usd"),
        ("2026-10-25", "usdfc_pool_volume_usd"),
        ("2026-10-26", "usdfc_pool_volume_usd"),
    }
    assert {r["method"] for r in rows} == {"backfill:filecoin.chain.love"}
    assert got[("2026-10-25", "usdfc_pool_volume_usd")]["observed_value"] == 9_000.0


def test_pool_days_past_the_lookback_are_skipped():
    oldest = OBS.epoch_at(OBS._anchor(datetime(2026, 10, 26, tzinfo=UTC)))
    rows = _pool_run(_FakeChain(oldest_block=oldest))
    assert {r["observed_at"] for r in rows} == {"2026-10-26"}


def test_the_swap_amount_is_read_as_signed():
    assert OBS._signed("f" * 64) == -1
    assert OBS._signed("0" * 63 + "5") == 5


def test_a_log_window_the_node_will_not_load_is_halved_until_it_does(monkeypatch):
    calls = []

    def rpc(endpoint, method, params, attempts=4):
        lo, hi = int(params[0]["fromBlock"], 16), int(params[0]["toBlock"], 16)
        calls.append((lo, hi))
        if lo <= 7 <= hi and hi - lo > 1:
            raise RuntimeError("eth_getLogs: failed to load event message")
        return [{"block": b} for b in range(lo, hi + 1)]

    monkeypatch.setattr(OBS, "_chain_rpc", rpc)
    chain = OBS.PoolChain.__new__(OBS.PoolChain)
    chain.endpoint, chain.pool = "http://x", "0xp"
    logs = chain.swap_logs(0, 15)
    assert [log["block"] for log in logs] == list(range(16))  # every epoch exactly once
    assert (0, 15) in calls and len(calls) > 1


def test_a_single_epoch_that_will_not_load_is_an_error_not_a_gap(monkeypatch):
    def rpc(endpoint, method, params, attempts=4):
        raise RuntimeError("eth_getLogs: failed to load event message")

    monkeypatch.setattr(OBS, "_chain_rpc", rpc)
    chain = OBS.PoolChain.__new__(OBS.PoolChain)
    chain.endpoint, chain.pool = "http://x", "0xp"
    with pytest.raises(RuntimeError):
        chain.swap_logs(0, 3)
