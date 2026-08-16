from pathlib import Path

from fpm import observations
from fpm.observations import (
    COLUMNS,
    append_observations,
    load_rows,
    merge,
    normalize_date,
    save_rows,
    to_row,
)
from fpm.observe import Observation


def _obs(**kwargs):
    base = dict(
        observed_at="2026-08-14",
        team="chainsafe",
        function_id="network-uptime",
        metric="uptime_ratio",
        observed_value=0.999,
        method="nightly",
    )
    return Observation(**{**base, **kwargs})


def test_normalize_date_truncates_an_instant():
    assert normalize_date("2026-07-19T12:00:00+00:00") == "2026-07-19"
    assert normalize_date("2026-07-19") == "2026-07-19"


def test_a_rerun_on_the_same_day_updates_rather_than_appends(tmp_path):
    path = tmp_path / "observations.csv"
    append_observations([_obs(observed_value=0.9)], path)
    rows = append_observations([_obs(observed_value=0.999)], path)
    assert len(rows) == 1
    assert rows[0]["observed_value"] == "0.999"  # last write wins: the re-run is the good reading


def test_an_instant_and_its_date_are_the_same_row(tmp_path):
    """The bug in the shipped CSV: 2026-07-19 and 2026-07-19T12:00:00+00:00 were two rows."""
    path = tmp_path / "observations.csv"
    save_rows([to_row(_obs(observed_at="2026-07-19T12:00:00+00:00"))], path)
    rows = append_observations([_obs(observed_at="2026-07-19")], path)
    assert len(rows) == 1
    assert rows[0]["observed_at"] == "2026-07-19"


def test_method_separates_provenance(tmp_path):
    path = tmp_path / "observations.csv"
    append_observations([_obs(method="nightly")], path)
    rows = append_observations([_obs(method="replay:api.github.com")], path)
    assert len(rows) == 2  # same metric-day, different provenance: both are real records


def test_history_is_preserved_across_appends(tmp_path):
    path = tmp_path / "observations.csv"
    append_observations([_obs(observed_at="2026-08-12")], path)
    append_observations([_obs(observed_at="2026-08-13")], path)
    rows = append_observations([_obs(observed_at="2026-08-14")], path)
    assert [r["observed_at"] for r in rows] == ["2026-08-12", "2026-08-13", "2026-08-14"]


def test_a_null_reading_round_trips_as_empty(tmp_path):
    path = tmp_path / "observations.csv"
    rows = append_observations([_obs(observed_value=None, note="fetch_error: boom")], path)
    assert rows[0]["observed_value"] == ""
    assert load_rows(path)[0]["note"] == "fetch_error: boom"


def test_columns_match_the_shipped_series():
    """The live CSV feeds the public static model and the dashboard; the header is a contract."""
    header = Path("data/observations.csv").read_text().splitlines()[0].split(",")
    assert header == COLUMNS


def test_merge_leaves_existing_rows_untouched():
    existing = [
        {
            "observed_at": "2025-07-01",
            "team": "filoz",
            "function_id": "builtin-actors",
            "metric": "release_age_days",
            "observed_value": "12.0",
            "method": "backfill:api.github.com",
            "note": "",
        }
    ]
    merged = merge(existing, [to_row(_obs())])
    assert len(merged) == 2
    assert existing[0] in merged


def test_columns_are_measurement_only():
    """Thresholds and outcomes live in fpm.thresholds and at render. A stored outcome is a
    frozen judgment against a bar that can change — which is how 2,398 rows came to be
    judged against an IPNI threshold nobody signed."""
    assert observations.COLUMNS == [
        "observed_at",
        "team",
        "function_id",
        "metric",
        "observed_value",
        "method",
        "note",
    ]


def test_the_shipped_csv_has_been_migrated():
    import csv

    with Path("data/observations.csv").open() as f:
        header = next(csv.reader(f))
    assert header == observations.COLUMNS


def test_indeterminate_is_still_signaled_by_an_empty_value():
    """The equivalence that makes dropping sla_outcome lossless: every indeterminate row had
    an empty observed_value, and no valued row was indeterminate. After migration the empty
    cell is the ONLY remaining signal, so blank rows must still be present and readable.

    Counts are not asserted — the file grows every night, and a test that has to be edited
    after each cron run is a test nobody trusts.
    """
    import csv

    rows = list(csv.DictReader(Path("data/observations.csv").open()))
    assert rows
    assert any(not r["observed_value"] for r in rows)
    assert all(set(r) == set(observations.COLUMNS) for r in rows)
