from datetime import datetime, timezone

from fpm.manifest import ExtractSpec
from fpm.reduce import derive_observed

REF = datetime(1970, 1, 1, 0, 10, 0, tzinfo=timezone.utc)  # epoch 600


def _ex(**kw):
    kw.setdefault("column", "v")
    return ExtractSpec(**kw)


def test_value_derive_defaults_to_reduce():
    rows = [{"v": 2}, {"v": 4}, {"v": 6}]
    assert derive_observed(rows, _ex(reduce="avg"), REF) == 4.0


def test_diff_on_single_row():
    rows = [{"expected": 10, "current": 8}]
    ex = _ex(column="expected", column2="current", reduce="single", derive="diff")
    assert derive_observed(rows, ex, REF) == 2.0


def test_diff_zero_when_in_sync():
    rows = [{"expected": 6279615, "current": 6279615}]
    ex = _ex(column="expected", column2="current", reduce="single", derive="diff")
    assert derive_observed(rows, ex, REF) == 0.0


def test_age_seconds_from_latest_row():
    rows = [{"height": 3, "ts": 100}, {"height": 5, "ts": 300}, {"height": 4, "ts": 200}]
    ex = _ex(column="ts", timestamp_column="height", reduce="latest", derive="age_seconds")
    assert derive_observed(rows, ex, REF) == 300.0  # 600 - 300 (latest by height)


def test_derive_none_on_missing_inputs():
    ex = _ex(column="expected", column2="current", reduce="single", derive="diff")
    assert derive_observed([], ex, REF) is None
    assert derive_observed([{"expected": 1}], ex, REF) is None  # column2 missing


def test_age_days_from_iso_date():
    ref = datetime(2000, 1, 31, tzinfo=timezone.utc)
    rows = [
        {"published_at": "1999-06-01T00:00:00Z"},
        {"published_at": "2000-01-01T00:00:00+00:00"},  # latest lexicographically
    ]
    ex = _ex(
        column="published_at",
        timestamp_column="published_at",
        cast="date",
        reduce="latest",
        derive="age_days",
    )
    assert derive_observed(rows, ex, ref) == 30.0  # Jan 31 - Jan 1


def test_null_ratio_counts_nulls_over_all_rows():
    rows = [
        {"last_error": None},
        {"last_error": "boom"},
        {"last_error": None},
        {"last_error": None},
    ]
    ex = _ex(column="last_error", reduce="null_ratio")
    assert derive_observed(rows, ex, REF) == 0.75  # 3 of 4 null (error-free)


def test_null_ratio_treats_missing_as_null():
    rows = [{}, {"last_error": "boom"}]
    ex = _ex(column="last_error", reduce="null_ratio")
    assert derive_observed(rows, ex, REF) == 0.5
