"""Voiding a reading that is wrong rather than missing."""

import pytest

from fpm import observations as obs
from scripts.observations import void_readings

ROW = {
    "observed_at": "2026-08-26",
    "team": "filecoin-data-portal",
    "function_id": "network-data-portal-pipeline-freshness",
    "metric": "pipeline_success_age_days",
    "observed_value": 36.629696,
    "method": "nightly",
    "note": "",
}


def _void(**over):
    base = {
        "date": ROW["observed_at"],
        "team": ROW["team"],
        "function_id": ROW["function_id"],
        "metric": ROW["metric"],
        "method": "nightly",
        "note": "measured against a stale run",
    }
    return {**base, **over}


def test_void_replaces_the_value_in_place(tmp_path):
    p = tmp_path / "obs.csv"
    obs.save_rows([ROW], p)
    void_readings([_void()], p)
    rows = obs.load_rows(p)
    assert len(rows) == 1, "a void must replace the reading, not land beside it"
    assert rows[0]["observed_value"] in (None, "")
    assert "stale run" in rows[0]["note"]


def test_void_leaves_a_recovered_backfill_row_untouched(tmp_path):
    """The true value is recovered under its own method and must survive the void."""
    p = tmp_path / "obs.csv"
    good = {**ROW, "observed_value": 0.634734, "method": "backfill:api.github.com"}
    obs.save_rows([ROW, good], p)
    void_readings([_void()], p)
    rows = obs.load_rows(p)
    kept = [r for r in rows if r["method"] == "backfill:api.github.com"]
    assert len(kept) == 1
    assert float(kept[0]["observed_value"]) == pytest.approx(0.634734)


def test_voiding_a_reading_that_does_not_exist_is_refused(tmp_path):
    """Otherwise a typo ADDS a null instead of replacing a value."""
    p = tmp_path / "obs.csv"
    obs.save_rows([ROW], p)
    with pytest.raises(SystemExit) as exc:
        void_readings([_void(date="2026-08-30")], p)
    assert "nothing to void" in str(exc.value)
    assert len(obs.load_rows(p)) == 1


def test_void_matches_on_method_so_it_cannot_hit_the_wrong_row(tmp_path):
    p = tmp_path / "obs.csv"
    obs.save_rows([ROW], p)
    with pytest.raises(SystemExit):
        void_readings([_void(method="live-review")], p)


def test_refusal_message_survives_a_caller_that_omits_method(tmp_path):
    """The default is documented as 'nightly', so the guard must not KeyError explaining itself."""
    p = tmp_path / "obs.csv"
    obs.save_rows([ROW], p)
    bare = {k: v for k, v in _void(date="2026-08-30").items() if k != "method"}
    with pytest.raises(SystemExit) as exc:
        void_readings([bare], p)
    assert "nightly" in str(exc.value)


def test_voiding_an_already_indeterminate_reading_is_refused(tmp_path):
    """Its note records WHY the day has no value; a void would overwrite that forensic trail."""
    p = tmp_path / "obs.csv"
    indeterminate = {**ROW, "observed_value": None, "note": "fetch_error: connection reset"}
    obs.save_rows([indeterminate], p)
    with pytest.raises(SystemExit) as exc:
        void_readings([_void()], p)
    assert "already indeterminate" in str(exc.value)
    assert "connection reset" in str(exc.value)
    assert obs.load_rows(p)[0]["note"] == "fetch_error: connection reset"
