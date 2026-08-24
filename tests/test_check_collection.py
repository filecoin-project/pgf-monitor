"""The blackout guard, offline.

What is being protected: a night on which every metric came back value-less must be
distinguishable from a night on which every source was healthy and quiet. Between 2026-08-22 and
2026-08-24 it was not, and three nights of point-in-time readings were lost.
"""

from pathlib import Path

from fpm.observations import collection_status, save_rows
from scripts.check_collection import main


def _row(day: str, fid: str, value: str) -> dict:
    return {
        "observed_at": day,
        "team": "ankr",
        "function_id": fid,
        "metric": "rpc_head_lag_epochs",
        "observed_value": value,
        "method": "nightly",
        "note": "",
    }


def _csv(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "observations.csv"
    save_rows(rows, p)
    return p


def test_a_day_where_nothing_carried_a_value_fails(tmp_path, capsys):
    p = _csv(tmp_path, [_row("2026-08-22", f"f{i}", "") for i in range(38)])
    assert main(["--as-of", "2026-08-22", "--csv", str(p)]) == 1
    assert "value-less" in capsys.readouterr().err


def test_a_day_with_no_rows_at_all_fails(tmp_path, capsys):
    """Distinct failure from a blackout: the run never reached the store."""
    p = _csv(tmp_path, [_row("2026-08-21", "f1", "3.0")])
    assert main(["--as-of", "2026-08-22", "--csv", str(p)]) == 1
    assert "no readings at all" in capsys.readouterr().err


def test_one_value_is_enough_to_pass(tmp_path):
    """The bar is deliberately a total blackout, not a share.

    Individual sources go quiet all the time -- 2 of 38 on 2026-08-20 -- and a guard that fires
    on those is a guard that gets muted. Only "not one metric could be read" is unambiguous.
    """
    rows = [_row("2026-08-22", f"f{i}", "") for i in range(37)] + [_row("2026-08-22", "ok", "4.0")]
    assert main(["--as-of", "2026-08-22", "--csv", str(_csv(tmp_path, rows))]) == 0


def test_a_healthy_day_passes(tmp_path, capsys):
    p = _csv(tmp_path, [_row("2026-08-24", f"f{i}", "1.5") for i in range(5)])
    assert main(["--as-of", "2026-08-24", "--csv", str(p)]) == 0
    assert "5 of 5" in capsys.readouterr().out


def test_status_counts_only_the_day_asked_for():
    rows = [_row("2026-08-22", "f1", ""), _row("2026-08-21", "f1", "9.0")]
    assert collection_status(rows, "2026-08-22") == (1, 0)
    assert collection_status(rows, "2026-08-21") == (1, 1)


def test_status_normalizes_the_date():
    """The file has carried both `2026-07-19` and `2026-07-19T12:00:00+00:00` for one metric-day;
    a guard that missed the timestamped form would read a full night as no rows at all."""
    assert collection_status([_row("2026-08-22T06:17:00+00:00", "f1", "2.0")], "2026-08-22") == (
        1,
        1,
    )
