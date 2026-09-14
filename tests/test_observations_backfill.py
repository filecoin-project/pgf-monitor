"""The arithmetic behind the 2026-08-22/23 outage recovery, offline.

The series builders in scripts/observations.py fetch, so they stay unit-untested like their
siblings. What IS tested here is the part that decides a number: how an age and a trailing
window are computed from an event history. Both are pinned against days the nightly actually
recorded, so if the method drifts these fail rather than silently producing plausible values.
"""

from datetime import datetime, timedelta

from scripts.observations import (
    TARGETED_ONLY,
    _anchor,
    age_days_at,
    select_strategies,
    trailing_window_sum,
)

# the full strategy set as backfill() declares it
ALL = {
    "usdfc-tvl",
    "blockscout",
    "releases",
    "ages",
    "snapshots",
    "status",
    "statuspage",
} | set(TARGETED_ONLY)


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# The data portal's successful pipeline runs, as fetched 2026-09-01. A run on every day of the
# outage is why this recovery is exact rather than an estimate.
PIPELINE_RUNS = [
    _dt("2026-08-19T14:23:58Z"),
    _dt("2026-08-20T14:27:01Z"),
    _dt("2026-08-21T14:25:40Z"),
    _dt("2026-08-22T14:13:09Z"),
    _dt("2026-08-23T14:15:22Z"),
    _dt("2026-08-24T14:33:09Z"),
    _dt("2026-08-25T14:35:59Z"),
]


def test_age_uses_the_newest_run_at_or_before_the_sample():
    # 08-22 05:30 reads the 08-21 14:25 run -- the 08-22 run has not happened yet at 05:30.
    age = age_days_at(PIPELINE_RUNS, _dt("2026-08-22T05:30:00Z"))
    assert age is not None
    expected = (_dt("2026-08-22T05:30:00Z") - _dt("2026-08-21T14:25:40Z")).total_seconds() / 86400
    assert abs(age - expected) < 1e-9
    assert 0.6 < age < 0.7  # same neighbourhood as the 08-21 and 08-24 nightly readings


def test_age_recovers_the_second_outage_day_independently():
    age = age_days_at(PIPELINE_RUNS, _dt("2026-08-23T05:30:00Z"))
    assert age is not None and 0.6 < age < 0.7


def test_age_is_none_before_any_run():
    assert age_days_at(PIPELINE_RUNS, _dt("2026-08-01T05:30:00Z")) is None


def test_age_does_not_look_into_the_future():
    """A sample minutes before a run must not report that run's age (which would be negative)."""
    age = age_days_at(PIPELINE_RUNS, _dt("2026-08-22T14:00:00Z"))
    assert age is not None and age > 0


def _hourly(start: str, values: list[float]) -> list[tuple[datetime, float]]:
    t0 = _dt(start)
    return [(t0 + timedelta(hours=i), v) for i, v in enumerate(values)]


def test_trailing_window_sums_only_the_preceding_24h():
    buckets = _hourly("2026-08-21T00:00:00Z", [100.0] * 72)
    total = trailing_window_sum(buckets, _dt("2026-08-22T05:30:00Z"))
    assert total == 2400.0  # exactly 24 buckets of 100


def test_trailing_window_excludes_the_sample_hour_itself():
    buckets = _hourly("2026-08-22T00:00:00Z", [1.0] * 10)
    # sample at 05:30 includes 00:00..05:00 (6 buckets), not 06:00
    assert trailing_window_sum(buckets, _dt("2026-08-22T05:30:00Z")) == 6.0


def test_trailing_window_is_none_when_no_bucket_falls_inside():
    buckets = _hourly("2026-08-25T00:00:00Z", [5.0] * 3)
    assert trailing_window_sum(buckets, _dt("2026-08-22T05:30:00Z")) is None


def test_trailing_window_differs_from_a_calendar_day():
    """Why hourly candles, not daily: the two definitions disagree.

    A calendar day would sum 08-21 00:00..23:00; the metric's h24 window at 05:30 spans
    08-21 05:30 -> 08-22 05:30. With a volume spike late on 08-21 the two diverge sharply.
    """
    buckets = _hourly("2026-08-21T00:00:00Z", [0.0] * 20 + [1000.0] * 4 + [0.0] * 24)
    calendar_day = sum(v for t, v in buckets if t.date().isoformat() == "2026-08-21")
    trailing = trailing_window_sum(buckets, _dt("2026-08-22T05:30:00Z"))
    assert calendar_day == 4000.0
    assert trailing == 4000.0
    # ... but read six hours earlier the spike has not happened yet
    assert trailing_window_sum(buckets, _dt("2026-08-21T18:00:00Z")) == 0.0


def test_anchor_follows_the_cron_change_on_2026_08_25():
    """observe.yml moved from a 06:17 cron to 05:23 on 2026-08-25.

    A single anchor is wrong on one side of that date. The outage days fall in the EARLIER era,
    which is the whole reason this is era-aware -- a 05:30 anchor reconstructed them 66 minutes
    early and disagreed with every neighbouring nightly reading by ~7%.
    """
    before = _anchor(_dt("2026-08-22T00:00:00Z"))
    after = _anchor(_dt("2026-08-31T00:00:00Z"))
    assert (before.hour, before.minute) == (6, 36)
    assert (after.hour, after.minute) == (5, 50)


def test_the_cron_change_day_itself_is_still_old_era():
    """8df156b landed 2026-08-25 06:59 UTC -- after that morning's 06:17 run.

    So 08-25 is old-era and 08-26 is the first new-era day. Off by one here left 08-25
    reconstructed 46.6 minutes early: 0.636701 against the nightly's 0.669067.
    """
    on_the_change_day = _anchor(_dt("2026-08-25T00:00:00Z"))
    first_new_era_day = _anchor(_dt("2026-08-26T00:00:00Z"))
    assert (on_the_change_day.hour, on_the_change_day.minute) == (6, 36)
    assert (first_new_era_day.hour, first_new_era_day.minute) == (5, 50)


# --- which strategies run, and when -----------------------------------------------------------


def test_default_rotation_excludes_the_targeted_recovery_strategies():
    """A plain `backfill` must not write the outage-recovery sources.

    Both emit a row per day for as far back as their source reaches (115 days of GitHub run
    history, 53 of GeckoTerminal candles), half of which lands beside an existing nightly
    reading. Useful when asked for, wrong as a side effect of the default --days 365.
    """
    chosen = select_strategies(sorted(ALL), None)
    assert "pipeline-success" not in chosen
    assert "pool-volume" not in chosen
    assert "ages" in chosen and "snapshots" in chosen  # the standing rotation is untouched


def test_only_reaches_a_targeted_strategy():
    assert select_strategies(sorted(ALL), ["pool-volume"]) == ["pool-volume"]


def test_only_follows_the_order_it_is_handed_not_the_argument_order():
    """Selection preserves `available`'s order, whatever that is -- not the caller's."""
    handed = ["zebra", "ages", "pool-volume"]
    assert select_strategies(handed, ["pool-volume", "ages"]) == ["ages", "pool-volume"]


def test_unknown_strategy_is_refused_rather_than_skipped():
    import pytest

    with pytest.raises(SystemExit) as exc:
        select_strategies(sorted(ALL), ["typo-here"])
    assert "typo-here" in str(exc.value)
    assert "choose from" in str(exc.value)


def test_targeted_only_names_are_checked_against_the_real_strategy_set():
    """Finding 5: a rename would otherwise silently re-admit a strategy to the default rotation.

    `backfill` asserts TARGETED_ONLY is a subset of its strategies dict. This test guards the
    invariant from the other side: every name must be selectable.
    """
    for name in TARGETED_ONLY:
        assert select_strategies(sorted(ALL), [name]) == [name]


# ---------------------------------------------------------------------------
# The reconstruction has to compute the SAME quantity the nightly does, from the SAME query.
# Both halves drifted apart on 2026-09-14 when the manifest moved off `?status=success` and off
# `created_at` (PR #71); a backfill left behind would have quietly written a neighbouring number
# under the right name, and inherited the stale-page fault the filter causes.
# ---------------------------------------------------------------------------


def _obs_module():
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("obs_pipe", "scripts/observations.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["obs_pipe"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_pipeline_backfill_asks_the_unfiltered_endpoint_and_uses_finish_times(monkeypatch):
    """One behavioral check over the three things that must match the manifest: the query it
    sends, the timestamp it measures from, and which runs it counts."""
    mod = _obs_module()
    seen = []

    def fake_get(url):
        seen.append(url)
        return {
            "workflow_runs": [
                # queued 17:09, finished 17:55 -- the manifest measures from the latter
                {
                    "created_at": "2026-09-13T17:09:32Z",
                    "updated_at": "2026-09-13T17:55:55Z",
                    "status": "completed",
                    "conclusion": "success",
                },
                # a FAILURE after it: counting this would report the pipeline healthier than it is
                {
                    "created_at": "2026-09-13T20:00:00Z",
                    "updated_at": "2026-09-13T20:30:00Z",
                    "status": "completed",
                    "conclusion": "failure",
                },
                # and a run still going: no success to measure yet
                {
                    "created_at": "2026-09-14T04:00:00Z",
                    "updated_at": "2026-09-14T04:10:00Z",
                    "status": "in_progress",
                    "conclusion": None,
                },
            ]
        }

    monkeypatch.setattr(mod, "_get", fake_get)
    monkeypatch.setattr(mod, "datetime", mod.datetime)
    rows = mod._pipeline_success_series(_dt("2026-09-13T00:00:00Z"))

    assert len(seen) == 1
    assert "status=success" not in seen[0], "the filtered query is what served months-old pages"
    assert "per_page=100" in seen[0]

    by_day = {r["observed_at"]: float(r["observed_value"]) for r in rows}
    assert "2026-09-14" in by_day, "the day after a successful run must be recoverable"
    # anchor 05:50 on 2026-09-14, measured from the 17:55:55 FINISH, not the 17:09:32 queue
    expected = (_dt("2026-09-14T05:50:00Z") - _dt("2026-09-13T17:55:55Z")).total_seconds() / 86400
    assert abs(by_day["2026-09-14"] - expected) < 1e-6  # rows are written rounded to 6dp
    # the created_at basis would read ~0.032 days higher; that is the drift being prevented
    queued = (_dt("2026-09-14T05:50:00Z") - _dt("2026-09-13T17:09:32Z")).total_seconds() / 86400
    assert abs(by_day["2026-09-14"] - queued) > 0.03
