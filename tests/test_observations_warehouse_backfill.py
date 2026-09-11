"""The one-time `warehouse` backfill: replaying an oso-sql statement per day.

Offline, with a fake client that answers from a dated table of its own, so the day loop and its
rules are testable without OSO_API_KEY or the network. The live path is proven separately by
scripts/live_oso_sql_smoke.py.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from datetime import datetime, timedelta, timezone

import pytest

from fpm.manifest import load_manifest
from fpm.transform.validate import validate_warehouse_sql

ALLOWED = {
    "filecoin.data_portal.daily_filecoin_pay_operators_metrics",
    "filecoin.data_portal.filecoin_pay_rails",
}


def _script():
    """scripts/observations.py is a script, not a package module — load it by path."""
    spec = importlib.util.spec_from_file_location("obs_script", "scripts/observations.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["obs_script"] = mod
    spec.loader.exec_module(mod)
    return mod


OBS = _script()
FN = load_manifest("tests/fixtures/filoz_oso_sql.yaml").functions[0]
TREE = validate_warehouse_sql(FN.source.sql, ALLOWED)
NOW = datetime(2026, 9, 10, tzinfo=timezone.utc)


class DatedFake:
    """Answers as a table holding one value per day, honouring the bound `:now` date.

    The statement asks for the newest day at or before `:now` within 4 days, so this reproduces
    that: the point is that the fake behaves like the warehouse, not like a constant.
    """

    def __init__(self, values: dict[str, float]):
        self.values = values
        self.calls: list[str] = []

    def query(self, sql: str) -> list[dict]:
        self.calls.append(sql)
        # The binder writes the date as a TIMESTAMP literal; take the first one.
        m = re.search(r"(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2}", sql)
        asked = datetime.fromisoformat(m.group(1)).date()
        candidates = [
            d
            for d in sorted(self.values)
            if datetime.fromisoformat(d).date() <= asked
            and (asked - datetime.fromisoformat(d).date()).days < 4
        ]
        if not candidates:
            return [{"_col0": None}]
        return [{"_col0": self.values[candidates[-1]]}]


def _rows(client, cutoff_days: int = 4, already=frozenset()):
    return OBS.warehouse_rows_for(
        FN, "filoz", TREE, client, NOW - timedelta(days=cutoff_days), NOW, already
    )


def test_emits_one_row_per_day_with_the_backfill_method():
    vals = {
        "2026-09-06": 1.0,
        "2026-09-07": 2.0,
        "2026-09-08": 3.0,
        "2026-09-09": 4.0,
        "2026-09-10": 5.0,
    }
    rows, skipped = _rows(DatedFake(vals))
    assert [r["observed_at"] for r in rows] == sorted(vals)
    assert [r["observed_value"] for r in rows] == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert {r["method"] for r in rows} == {"backfill:oso-warehouse"}
    assert {r["team"] for r in rows} == {"filoz"}
    assert {r["metric"] for r in rows} == {FN.sla.metric}
    assert skipped == 0


def test_a_late_source_reconstructs_as_a_plateau_and_that_is_correct():
    """The tail repeats the newest available value, which is what a nightly would have read.

    Deduping it would be wrong: it would hide that the source was late and make the backfilled
    half of the series mean something different from the nightly half.
    """
    rows, _ = _rows(DatedFake({"2026-09-06": 1.0, "2026-09-08": 18801.89}))
    by_day = {r["observed_at"]: r["observed_value"] for r in rows}
    assert by_day["2026-09-08"] == by_day["2026-09-09"] == by_day["2026-09-10"] == 18801.89


def test_days_already_recorded_are_skipped_whatever_recorded_them():
    """row_key includes method, so a second row for a recorded day would double-count on charts."""
    vals = {f"2026-09-0{d}": float(d) for d in (6, 7, 8, 9)}
    vals["2026-09-10"] = 10.0
    already = {("2026-09-07", "filoz", FN.function_id, FN.sla.metric)}
    rows, skipped = _rows(DatedFake(vals), already=already)
    assert skipped == 1
    assert "2026-09-07" not in {r["observed_at"] for r in rows}
    assert len(rows) == 4


def test_a_day_the_source_cannot_answer_emits_nothing_rather_than_a_null():
    """A day the warehouse never covered is not a fact about the metric; a null would read as
    an outage we caused."""
    rows, _ = _rows(DatedFake({"2026-09-10": 5.0}))
    # Only 09-10 is answerable: the earlier days have no value within the 4-day floor.
    assert [r["observed_at"] for r in rows] == ["2026-09-10"]
    assert all(r["observed_value"] is not None for r in rows)


def test_an_empty_source_emits_no_rows_at_all():
    rows, _ = _rows(DatedFake({}))
    assert rows == []


def test_a_query_error_skips_only_that_day():
    class Flaky(DatedFake):
        def query(self, sql):
            if "2026-09-08" in sql:
                raise RuntimeError("trino hiccup")
            return super().query(sql)

    vals = {f"2026-09-0{d}": float(d) for d in (6, 7, 8, 9)}
    vals["2026-09-10"] = 10.0
    rows, _ = _rows(Flaky(vals))
    days = {r["observed_at"] for r in rows}
    assert "2026-09-08" not in days
    assert {"2026-09-06", "2026-09-07", "2026-09-09", "2026-09-10"} <= days


def test_one_query_per_day_in_the_window():
    client = DatedFake({"2026-09-10": 1.0})
    _rows(client, cutoff_days=9)
    assert len(client.calls) == 10  # inclusive of both ends


def test_the_window_is_bounded_by_now_not_by_the_source():
    """A source with future rows must not produce rows dated after the run."""
    vals = {"2026-09-10": 1.0, "2026-09-11": 2.0, "2026-09-30": 3.0}
    rows, _ = _rows(DatedFake(vals), cutoff_days=1)
    assert max(r["observed_at"] for r in rows) == "2026-09-10"


def test_warehouse_is_not_in_the_default_rotation():
    """A bare `backfill` must not fire ~365 Trino queries per oso-sql metric as a side effect."""
    assert "warehouse" in OBS.TARGETED_ONLY
    assert "warehouse" not in OBS.select_strategies(["releases", "warehouse"], None)
    assert OBS.select_strategies(["releases", "warehouse"], ["warehouse"]) == ["warehouse"]


def test_an_unknown_strategy_name_is_refused_rather_than_silently_skipped():
    """It exits rather than raising a ValueError, so catch SystemExit (a BaseException)."""
    with pytest.raises(SystemExit, match="unknown strategy: wharehouse"):
        OBS.select_strategies(["warehouse"], ["wharehouse"])


# --- regressions from the 2026-09-11 review ---


def test_the_cadence_window_is_bound_not_a_zero_width_one():
    """The nightly binds `window_for(cadence, as_of)`, so the replay must bind the same thing.

    Binding day/day/day gave window_start == window_end: harmless for a `:now`-only statement,
    but a metric aggregating over :window_start/:window_end would silently backfill empty-window
    numbers into the system of record under a note claiming it replayed the manifest's statement.
    """
    from fpm.domain import window_for
    from fpm.transform.validate import validate_warehouse_sql as _v

    windowed = _v(
        "SELECT COUNT(*) FROM filecoin.data_portal.filecoin_pay_rails "
        "WHERE created_at >= :window_start AND created_at < :window_end",
        ALLOWED,
    )

    class Capture(DatedFake):
        def query(self, sql):
            self.calls.append(sql)
            return [{"_col0": 1.0}]

    client = Capture({})
    day = NOW - timedelta(days=1)
    OBS.warehouse_rows_for(FN, "filoz", windowed, client, day, day, frozenset())
    expected = window_for(FN.sla.cadence, day.replace(hour=0, minute=0, second=0, microsecond=0))
    assert expected.start != expected.end  # the window has real width
    assert expected.start.strftime("%Y-%m-%d %H:%M:%S") in client.calls[0]
    assert expected.end.strftime("%Y-%m-%d %H:%M:%S") in client.calls[0]


def test_date_filter_is_applied_before_querying_not_to_the_results():
    """Every other strategy fetches a bulk history once, so filtering output is free. This one
    issues a query per day, so an output filter would still fire ~365 of them to keep one row."""
    client = DatedFake({"2026-09-08": 1.0, "2026-09-09": 2.0, "2026-09-10": 3.0})
    rows, _ = OBS.warehouse_rows_for(
        FN, "filoz", TREE, client, NOW - timedelta(days=9), NOW, frozenset(), {"2026-09-09"}
    )
    assert [r["observed_at"] for r in rows] == ["2026-09-09"]
    assert len(client.calls) == 1  # nine other days were never queried
