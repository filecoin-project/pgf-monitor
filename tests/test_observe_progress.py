"""The nightly run is unattended and slow, so its log is the only window into it.

stdout is block-buffered whenever it is not a tty — which is always, under GitHub Actions. An
unflushed run shows an empty log for an hour and then everything at once, which makes a hang
indistinguishable from slow progress. These tests pin the parts of that window that matter.
"""

import subprocess
import sys


def _run(tmp_path, *args):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "fpm.cli",
            "observe",
            "chainsafe",
            "--registry",
            "tests/fixtures",
            "--as-of",
            "2026-08-14",
            "--csv",
            str(tmp_path / "observations.csv"),
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_progress_reaches_a_redirected_log(tmp_path):
    """Not a tty: without an explicit flush this output would not appear until the process ends."""
    out = _run(tmp_path, "--dry-run").stdout
    assert "[1/1] chainsafe" in out
    assert "uptime_ratio" in out  # the per-metric line, not just the per-team summary


def test_it_reports_which_metrics_yielded_no_value(tmp_path):
    """A blank reading is a source that stopped answering, not a neutral gap. Name it in the log."""
    out = _run(tmp_path, "--dry-run").stdout
    assert "no value from 1 metrics:" in out
    assert "chainsafe/forest-snapshots" in out


def test_dry_run_writes_nothing(tmp_path):
    _run(tmp_path, "--dry-run")
    assert not (tmp_path / "observations.csv").exists()


def test_a_real_run_writes_the_csv(tmp_path):
    result = _run(tmp_path)
    assert result.returncode == 0
    assert (tmp_path / "observations.csv").exists()


def test_blanks_are_grouped_by_host(tmp_path):
    """The shape of a failure names its cause: many hosts = many broken sources; ONE host =
    one problem (rate limit, outage, expired credential). The paginator bug read as 14
    unrelated broken metrics for a month because nothing grouped them."""
    out = _run(tmp_path, "--dry-run").stdout
    assert "no value from 1 metrics:" in out
    # chainsafe's fixture source has no base_url, so it groups under "none" — the grouping
    # line must still be present and carry the count.
    assert any(line.strip().endswith(": 1") for line in out.splitlines())
