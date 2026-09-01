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
    "usdfc-tvl", "blockscout", "releases", "ages", "snapshots", "status", "statuspage",
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


def test_anchor_boundary_is_inclusive_of_the_new_era():
    on_the_day = _anchor(_dt("2026-08-25T00:00:00Z"))
    assert (on_the_day.hour, on_the_day.minute) == (5, 50)


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


def test_only_preserves_declaration_order_not_argument_order():
    chosen = select_strategies(sorted(ALL), ["pool-volume", "ages"])
    assert chosen == [s for s in sorted(ALL) if s in {"pool-volume", "ages"}]


def test_unknown_strategy_is_refused_rather_than_skipped():
    import pytest

    with pytest.raises(SystemExit) as exc:
        select_strategies(sorted(ALL), ["typo-here"])
    assert "typo-here" in str(exc.value)
    assert "choose from" in str(exc.value)
