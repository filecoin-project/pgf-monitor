"""fpm.thresholds is the only writer of data/thresholds.csv. These lock its contract."""

import csv
from dataclasses import dataclass
from pathlib import Path

import yaml

from fpm import thresholds


@dataclass
class Rec:
    observed_at: str
    team: str
    function_id: str
    metric: str
    threshold_op: str | None
    threshold_value: float | None
    source: str


def _rec(**kw):
    base = dict(
        observed_at="2026-08-16",
        team="oif-ipni",
        function_id="content-routing-ipni",
        metric="ipni_error_free_ratio",
        threshold_op=">=",
        threshold_value=0.90,
        source="signed-appendix",
    )
    base.update(kw)
    return Rec(**base)


def test_columns_are_exactly_the_seven_agreed(tmp_path):
    assert thresholds.COLUMNS == [
        "observed_at",
        "team",
        "function_id",
        "metric",
        "threshold_op",
        "threshold_value",
        "source",
    ]


def test_a_row_round_trips(tmp_path):
    p = tmp_path / "t.csv"
    thresholds.append_thresholds([_rec()], p)
    [row] = thresholds.load_rows(p)
    assert row["threshold_op"] == ">="
    assert float(row["threshold_value"]) == 0.90
    assert row["source"] == "signed-appendix"


def test_no_threshold_writes_empty_cells_not_zero(tmp_path):
    """Empty means 'no agreed SLA'. A 0.0 would silently become a real, and absurd, bar."""
    p = tmp_path / "t.csv"
    thresholds.append_thresholds(
        [_rec(threshold_op=None, threshold_value=None, source="provisional")], p
    )
    [row] = thresholds.load_rows(p)
    assert row["threshold_op"] == ""
    assert row["threshold_value"] == ""


def test_an_iso_instant_is_truncated_to_its_utc_date(tmp_path):
    p = tmp_path / "t.csv"
    thresholds.append_thresholds([_rec(observed_at="2026-08-16T06:17:00+00:00")], p)
    [row] = thresholds.load_rows(p)
    assert row["observed_at"] == "2026-08-16"


def test_the_same_day_is_replaced_not_appended(tmp_path):
    """Last-wins on (date, team, function, metric): a re-run must correct the day, not
    double it. The key deliberately omits `method` — that is a property of the measurement,
    not of the commitment."""
    p = tmp_path / "t.csv"
    thresholds.append_thresholds([_rec(threshold_value=0.95)], p)
    rows = thresholds.append_thresholds([_rec(threshold_value=0.90)], p)
    assert len(rows) == 1
    assert float(rows[0]["threshold_value"]) == 0.90


def test_distinct_days_accumulate_so_a_change_is_visible(tmp_path):
    p = tmp_path / "t.csv"
    thresholds.append_thresholds([_rec(observed_at="2026-08-15", threshold_value=0.95)], p)
    rows = thresholds.append_thresholds(
        [_rec(observed_at="2026-08-16", threshold_value=0.90)], p
    )
    assert [r["threshold_value"] for r in rows] == ["0.95", "0.9"]


def test_loading_a_missing_file_is_empty(tmp_path):
    assert thresholds.load_rows(tmp_path / "nope.csv") == []


def test_every_shipped_threshold_row_maps_to_a_real_registry_function():
    """Every (team, function_id) in the committed data/thresholds.csv must exist in that
    team's registry/<team>.yaml functions[]. This is not a hypothetical: test-fixture rows
    once leaked into this production file — chainsafe/forest-snapshots and
    chainsafe/network-uptime, which exist only in tests/fixtures/chainsafe.yaml, not in
    registry/chainsafe.yaml — and only a manual review caught it. This test encodes that
    invariant so CI catches a recurrence, whether it comes from a stray test write, a hand
    edit, or a draft merged prematurely."""
    registry_dir = Path("registry")
    rows = list(csv.DictReader(Path("data/thresholds.csv").open()))
    assert rows

    teams = {r["team"] for r in rows}
    function_ids_by_team: dict[str, set[str]] = {}
    for team in teams:
        manifest_path = registry_dir / f"{team}.yaml"
        assert manifest_path.exists(), f"registry/{team}.yaml does not exist for team {team!r}"
        raw = yaml.safe_load(manifest_path.read_text())
        function_ids_by_team[team] = {fn["function_id"] for fn in raw["functions"]}

    missing = [
        (r["team"], r["function_id"])
        for r in rows
        if r["function_id"] not in function_ids_by_team[r["team"]]
    ]
    assert missing == []
