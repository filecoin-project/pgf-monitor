"""The two structural exports, and the guard that the committed CSVs still match the registry."""

from pathlib import Path

from fpm.exports import (
    FUNCTIONS_COLUMNS,
    FUNCTIONS_CSV,
    METRICS_COLUMNS,
    METRICS_CSV,
    function_rows,
    load_rows,
    metric_rows,
    save_rows,
    unresolved_kernel_ids,
)
from fpm.kernel import load_kernel


def test_function_rows_cover_the_whole_inventory():
    kernel = load_kernel()
    rows = function_rows(kernel)
    assert len(rows) == len(kernel.entries)
    # The uncovered functions are the point of publishing this table: a denominator drawn from
    # covered functions only would always read 100%.
    measured = {r["kernel_id"] for r in metric_rows()}
    assert {r["kernel_id"] for r in rows} - measured


def test_metric_rows_carry_the_join_keys():
    rows = metric_rows()
    adopted = [r for r in rows if r["state"] == "adopted"]
    assert adopted
    assert all(r["team"] and r["metric"] and r["kernel_id"] for r in adopted)
    # grant_ref is Karma's own id and the key this export exists to expose. The one adopted entry
    # without one is the filfox cross-check, which no grant pays for.
    assert sum(1 for r in adopted if not r["grant_ref"]) <= 1


def test_drafts_are_included_and_labelled():
    states = {r["state"] for r in metric_rows()}
    assert states == {"adopted", "draft"}


def test_a_metric_in_both_files_yields_a_row_per_state(tmp_path):
    (tmp_path / "drafts").mkdir()
    Path("tests/fixtures/chainsafe_oso.yaml").read_text()
    for d in (tmp_path, tmp_path / "drafts"):
        (d / "acme.yaml").write_text(Path("tests/fixtures/chainsafe_oso.yaml").read_text())
    rows = metric_rows(tmp_path)
    assert [r["state"] for r in rows if r["function_id"] == rows[0]["function_id"]] == [
        "adopted",
        "draft",
    ]


def test_every_kernel_id_in_the_registry_resolves():
    assert unresolved_kernel_ids(metric_rows()) == []


def test_committed_csvs_match_the_registry():
    """The CSVs are DERIVED. If this fails, run `uv run python scripts/exports.py write`.

    Without this the published tables drift from `registry/` silently, which is the same class of
    failure as a dashboard rendering a threshold nobody agreed to.
    """
    assert load_rows(FUNCTIONS_CSV) == [
        {c: str(r.get(c, "")) for c in FUNCTIONS_COLUMNS} for r in function_rows()
    ]
    assert load_rows(METRICS_CSV) == [
        {c: str(r.get(c, "")) for c in METRICS_COLUMNS} for r in metric_rows()
    ]


def test_round_trip_through_csv(tmp_path):
    path = tmp_path / "f.csv"
    rows = function_rows()
    save_rows(rows, FUNCTIONS_COLUMNS, path)
    assert load_rows(path) == [{c: str(r.get(c, "")) for c in FUNCTIONS_COLUMNS} for r in rows]
