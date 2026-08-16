import csv as _csv
import shutil

from fpm.cli import main


def _registry(tmp_path):
    d = tmp_path / "registry"
    d.mkdir()
    shutil.copy("tests/fixtures/chainsafe.yaml", d / "chainsafe.yaml")
    return str(d)


def test_observe_writes_both_csvs(tmp_path):
    """The two tables are written by the same run, so their observed_at values agree by
    construction. A threshold row for a day with no observation row would never join."""
    obs_csv = tmp_path / "observations.csv"
    thr_csv = tmp_path / "thresholds.csv"
    rc = main(
        [
            "observe",
            "--registry", _registry(tmp_path),
            "--fixtures", "fixtures/responses",
            "--as-of", "2026-08-16",
            "--csv", str(obs_csv),
            "--thresholds-csv", str(thr_csv),
        ]
    )
    assert rc == 0
    obs = list(_csv.DictReader(obs_csv.open()))
    thr = list(_csv.DictReader(thr_csv.open()))
    assert len(thr) == len(obs)
    assert {(r["team"], r["function_id"], r["metric"], r["observed_at"]) for r in thr} == {
        (r["team"], r["function_id"], r["metric"], r["observed_at"]) for r in obs
    }


def test_observe_dry_run_writes_no_thresholds(tmp_path):
    thr_csv = tmp_path / "thresholds.csv"
    main(
        [
            "observe",
            "--registry", _registry(tmp_path),
            "--fixtures", "fixtures/responses",
            "--as-of", "2026-08-16",
            "--csv", str(tmp_path / "observations.csv"),
            "--thresholds-csv", str(thr_csv),
            "--dry-run",
        ]
    )
    assert not thr_csv.exists()


def test_cli_dev_auto_approve(tmp_path, capsys):
    code = main(
        [
            "review",
            "chainsafe",
            "--manifest",
            "tests/fixtures/chainsafe.yaml",
            "--store",
            str(tmp_path),
            "--as-of",
            "2026-07-01",
            "--dev-auto-approve",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "network-uptime" in out and "pass" in out and "meeting" in out
    assert "forest-snapshots" in out and "indeterminate" in out and "pending_review" in out
