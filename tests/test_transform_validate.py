from datetime import datetime, timezone

import pytest

from fpm.transform.validate import (
    TransformSqlError,
    bind_transform_sql,
    validate_transform_sql,
)

WS = datetime(2026, 6, 1, tzinfo=timezone.utc)
WE = datetime(2026, 7, 1, tzinfo=timezone.utc)
NOW = datetime(2026, 7, 1, 12, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT approx_percentile(latency_ms, 0.95) FROM raw",
        "SELECT CAST(SUM(CASE WHEN ok THEN 1 ELSE 0 END) AS DOUBLE) / COUNT(*) FROM raw",
        "SELECT avg(v) FROM raw WHERE ts >= :window_start",
        "SELECT max(raw) FROM raw",
    ],
)
def test_accepts_valid_transforms(sql):
    assert validate_transform_sql(sql) is not None


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT count(*) FROM oso.projects_v1",  # foreign table
        "SELECT count(*) FROM raw JOIN secrets ON raw.id = secrets.id",  # join to foreign
        "DROP TABLE raw",  # ddl
        "DELETE FROM raw",  # dml
        "SELECT 1 FROM raw; DROP TABLE raw",  # multi-statement
        "SELECT avg(a), avg(b) FROM raw",  # multi-column
        "SELECT 1",  # no table
        "SELECT (((",  # unparseable
    ],
)
def test_rejects_unsafe_transforms(sql):
    with pytest.raises(TransformSqlError):
        validate_transform_sql(sql)


def test_rejects_unknown_bind_token():
    with pytest.raises(TransformSqlError):
        validate_transform_sql("SELECT avg(v) FROM raw WHERE ts >= :window_stat")


def test_bind_swaps_table_not_column():
    tree = validate_transform_sql("SELECT max(raw) FROM raw")
    out = bind_transform_sql(tree, "cat.sch.tbl", WS, WE, NOW)
    assert "cat.sch.tbl" in out
    assert "MAX(RAW)" in out.upper()  # the column named `raw` is left untouched


def test_bind_substitutes_window_token():
    tree = validate_transform_sql("SELECT avg(v) FROM raw WHERE ts >= :window_start")
    out = bind_transform_sql(tree, "cat.sch.tbl", WS, WE, NOW)
    assert ":window_start" not in out
    assert "2026-06-01 00:00:00" in out  # Trino format: space separator
    assert "2026-06-01T" not in out  # not ISO-T
    assert "+00:00" not in out  # no timezone offset in a bare TIMESTAMP literal
    assert "cat.sch.tbl" in out


def test_accepts_tz_bind_tokens():
    # the _tz variants match dlt-parsed `timestamp with time zone` columns
    validate_transform_sql("SELECT avg(v) FROM raw WHERE ts >= :window_start_tz")
    validate_transform_sql("SELECT max(ts) FROM raw WHERE ts <= :now_tz")
    validate_transform_sql("SELECT count(*) FROM raw WHERE ts < :window_end_tz")


def test_bind_tz_token_emits_timestamp_with_time_zone():
    tree = validate_transform_sql("SELECT max(ts) FROM raw WHERE ts >= :window_start_tz")
    out = bind_transform_sql(tree, "cat.sch.tbl", WS, WE, NOW)
    assert ":window_start_tz" not in out
    assert "TIMESTAMP WITH TIME ZONE" in out.upper()
    assert "2026-06-01 00:00:00 +00:00" in out


def test_naive_and_tz_tokens_differ():
    naive = bind_transform_sql(
        validate_transform_sql("SELECT count(*) FROM raw WHERE ts >= :now"), "t.t.t", WS, WE, NOW
    )
    tz = bind_transform_sql(
        validate_transform_sql("SELECT count(*) FROM raw WHERE ts >= :now_tz"), "t.t.t", WS, WE, NOW
    )
    assert "WITH TIME ZONE" not in naive.upper()
    assert "WITH TIME ZONE" in tz.upper()


def test_rejects_unknown_token_even_with_tz_set_present():
    with pytest.raises(TransformSqlError):
        validate_transform_sql("SELECT avg(v) FROM raw WHERE ts >= :window_stat_tz")
