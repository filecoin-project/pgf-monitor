"""Reading PDP active proof sets at a past block, for nights the nightly lost.

The counter has no time dimension and cannot be rebuilt from events (docs/metric-history.md), but
it can be READ at a past block: from the subgraph while it retains the block, and from PDPVerifier
on chain once it does not. The second is a different computation, so most of these tests are about
refusing to use it unless it reproduces the first.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone

import pytest

UTC = timezone.utc


def _script():
    spec = importlib.util.spec_from_file_location("obs_pdp", "scripts/observations.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["obs_pdp"] = mod
    spec.loader.exec_module(mod)
    return mod


OBS = _script()
NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
KEYS = ("filoz", "fid", "met")


def _subgraph(first_block: int, value: int = 956):
    def read(endpoint, block):
        if block < first_block:
            raise OBS.SubgraphPruned(f"only has data starting at block {first_block}")
        return value

    return read


def _run(monkeypatch, subgraph, chain, have_value=frozenset(), days=3):
    monkeypatch.setattr(OBS, "pdp_proofsets_target", lambda *a, **k: (*KEYS, "http://x"))
    return OBS._pdp_proofsets_series(
        NOW - timedelta(days=days), NOW, set(have_value), subgraph=subgraph, chain=chain
    )


def test_retained_days_are_read_from_the_subgraph_itself(monkeypatch):
    def chain(block):
        raise AssertionError("the chain must not be asked while the subgraph answers")

    rows = _run(monkeypatch, _subgraph(0), chain)
    assert {r["observed_at"] for r in rows} == {
        "2026-10-12",
        "2026-10-13",
        "2026-10-14",
        "2026-10-15",
    }
    assert {r["method"] for r in rows} == {"backfill:api.goldsky.com"}


def test_pruned_days_fall_back_to_the_chain_after_the_check(monkeypatch):
    first = OBS.epoch_at(datetime(2026, 10, 14, 0, 23, tzinfo=UTC))
    asked = []

    def chain(block):
        asked.append(block)
        return 956 if block >= first else 1000

    rows = _run(monkeypatch, _subgraph(first), chain)
    by_day = {r["observed_at"]: r for r in rows}
    assert by_day["2026-10-13"]["method"] == "backfill:api.node.glif.io"
    assert by_day["2026-10-13"]["observed_value"] == 1000
    assert by_day["2026-10-14"]["method"] == "backfill:api.goldsky.com"
    # the check runs once, at a recent block, before the first chain-derived row
    assert asked[0] > OBS.epoch_at(datetime(2026, 10, 15, tzinfo=UTC))


def test_it_refuses_the_chain_when_it_disagrees_with_the_subgraph(monkeypatch):
    first = OBS.epoch_at(datetime(2026, 10, 14, tzinfo=UTC))
    with pytest.raises(RuntimeError, match="NOT the nightly's quantity"):
        _run(monkeypatch, _subgraph(first, value=956), lambda block: 1171)


def test_a_null_nightly_is_filled_but_a_valued_day_is_not(monkeypatch):
    have = {("2026-10-14", *KEYS)}
    rows = _run(monkeypatch, _subgraph(0), lambda b: 0, have_value=have)
    assert "2026-10-14" not in {r["observed_at"] for r in rows}


def test_samples_are_taken_at_the_nightly_anchor(monkeypatch):
    seen = []

    def subgraph(endpoint, block):
        seen.append(block)
        return 1

    _run(monkeypatch, subgraph, lambda b: 0, days=1)
    assert OBS.epoch_at(OBS._anchor(datetime(2026, 10, 14, tzinfo=UTC))) in seen


def test_epoch_matches_a_known_block():
    # observed live 2026-10-15: block 6458733 carries timestamp 1792068390
    assert OBS.epoch_at(datetime.fromtimestamp(1792068390, UTC)) == 6458733


def test_a_failed_eth_call_refuses_rather_than_undercounts():
    def rpc(batch):
        if batch[0]["params"][0]["data"].startswith("0x" + OBS._SEL_NEXT_DATASET_ID):
            return [{"id": 1, "result": hex(3)}]
        return [{"id": b["id"], "result": hex(1)} for b in batch[:-1]] + [
            {"id": batch[-1]["id"], "error": {"message": "lookback"}}
        ]

    with pytest.raises(RuntimeError, match="dataSetLive"):
        OBS.pdp_active_at_chain(100, rpc=rpc)


def test_chain_count_counts_live_ids_below_next_id():
    def rpc(batch):
        if batch[0]["params"][0]["data"].startswith("0x" + OBS._SEL_NEXT_DATASET_ID):
            return [{"id": 1, "result": hex(5)}]
        return [{"id": b["id"], "result": hex(b["id"] % 2)} for b in batch]

    assert OBS.pdp_active_at_chain(100, rpc=rpc, chunk=2) == 2  # ids 1 and 3


def test_the_real_target_is_found_by_endpoint_and_matches_the_registry():
    team, fid, metric, endpoint = OBS.pdp_proofsets_target()
    assert OBS._PDP_SUBGRAPH_MARKER in endpoint
    assert (team, fid, metric) == ("filoz", "curio-pdp-active-proofsets", "pdp_active_proof_sets")


def test_pdp_proofsets_is_not_in_the_default_rotation():
    assert "pdp-proofsets" in OBS.TARGETED_ONLY
    assert "pdp-proofsets" not in OBS.select_strategies(["releases", "pdp-proofsets"], None)
