"""A slow night must cost the readings it could not take, and nothing more.

On 2026-09-18 an OSO-side stall made every ingestion poll run to its 30x10s ceiling. The nightly
job hit the 60-minute cap four manifests in, was cancelled mid-loop, and the whole day was lost --
including the 20 readings it had already collected, because `run_observe_cli` accumulated
everything and appended once at the end. The commit step never ran, so the series shows a hole on
a night when two thirds of the sources were answering perfectly well.

Three properties pinned here, all offline:

- readings persist per MANIFEST, so a killed process keeps every completed team;
- a deadline stops the loop cleanly instead of letting the runner SIGKILL it mid-write;
- a function nobody got to still gets a row saying so, because a missing row is
  indistinguishable from a day the monitor did not run -- the same argument
  `thresholds_for` already makes about absent commitments.

The deadline is expressed as a `should_continue` predicate rather than a clock so these tests
need no sleeping and no monkeypatched time.
"""

from datetime import datetime, timezone
from pathlib import Path

from fpm.cli import order_by_cost
from fpm.manifest import load_manifest
from fpm.observe import TRUNCATED_NOTE, observe

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
FIXTURES = Path("fixtures/responses")
MANIFEST = "tests/fixtures/chainsafe.yaml"  # 2 functions


def _observe(**kwargs):
    return observe(manifest_path=MANIFEST, fixtures_dir=FIXTURES, as_of=AS_OF, **kwargs)


# ----------------------------------------------------------------- ordering


def test_cheap_manifests_are_measured_first():
    """Cheapest-first so a short night collects as many commitments as it can.

    Function count is the cost proxy rather than a stored duration table: it tracked the real
    times closely on 2026-09-17 (1 function/35s, 2/68s, 5/170s) and cannot go stale.
    """
    paths = [
        Path(f"tests/fixtures/{n}.yaml") for n in ("kernel_demo", "chainsafe", "chainsafe_oso")
    ]
    assert [p.stem for p in order_by_cost(paths)] == [
        "chainsafe_oso",  # 1
        "chainsafe",  # 2
        "kernel_demo",  # 4
    ]


def test_ties_break_by_name_so_the_order_is_deterministic():
    """Two manifests of equal cost must not swap between runs; a reader comparing two nights'
    logs should see the same sequence."""
    paths = [Path(f"tests/fixtures/{n}.yaml") for n in ("filoz_oso_sql", "chainsafe_oso")]
    assert [p.stem for p in order_by_cost(paths)] == ["chainsafe_oso", "filoz_oso_sql"]
    assert order_by_cost(list(reversed(paths))) == order_by_cost(paths)


def test_ordering_does_not_drop_or_duplicate_a_manifest():
    paths = [
        Path(f"tests/fixtures/{n}.yaml") for n in ("kernel_demo", "chainsafe", "filoz_oso_sql")
    ]
    assert sorted(order_by_cost(paths)) == sorted(paths)


# --------------------------------------------------------------- truncation


def test_a_truncated_run_still_returns_one_observation_per_function():
    """`observe` promises one Observation per function, always. Truncation does not get to
    break that promise -- it changes what the rows SAY, not whether they exist."""
    obs = _observe(should_continue=lambda: False)
    manifest = load_manifest(MANIFEST)
    assert [o.function_id for o in obs] == [f.function_id for f in manifest.functions]


def test_an_unattempted_function_carries_no_value_and_says_why():
    """A row with no note would read as a source that went dark. It was never asked."""
    obs = _observe(should_continue=lambda: False)
    for o in obs:
        assert o.observed_value is None
        assert o.outcome == "indeterminate"
        assert TRUNCATED_NOTE in o.note


def test_work_completed_before_the_deadline_is_kept():
    """The whole point: the metrics that DID read keep their real values."""
    calls = []

    def once() -> bool:
        calls.append(1)
        return len(calls) <= 1  # measure the first function, truncate the rest

    obs = _observe(should_continue=once)
    assert obs[0].observed_value is not None
    assert TRUNCATED_NOTE not in obs[0].note
    assert obs[1].observed_value is None
    assert TRUNCATED_NOTE in obs[1].note


def test_no_predicate_means_no_truncation():
    """The default path is unchanged: every function is measured for real."""
    obs = _observe()
    assert all(TRUNCATED_NOTE not in o.note for o in obs)


def test_the_progress_callback_does_not_fire_for_unattempted_functions():
    """The log line reports what a metric did. Nothing was done, so nothing is reported --
    otherwise a truncated night looks in the log exactly like a night of broken sources."""
    seen = []
    _observe(should_continue=lambda: False, on_observation=seen.append)
    assert seen == []


# ------------------------------------------------- the CLI, end to end offline

import subprocess  # noqa: E402
import sys  # noqa: E402


def _cli(tmp_path, *args, registry="tests/fixtures"):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "fpm.cli",
            "observe",
            "--registry",
            registry,
            "--as-of",
            "2026-08-14",
            "--csv",
            str(tmp_path / "observations.csv"),
            "--thresholds-csv",
            str(tmp_path / "thresholds.csv"),
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_an_expired_deadline_still_writes_a_row_for_every_commitment(tmp_path):
    """--deadline-minutes 0 is already spent at the first check, so nothing is measured. The
    series must still say so for every commitment rather than showing a hole."""
    result = _cli(tmp_path, "chainsafe", "--deadline-minutes", "0")
    body = (tmp_path / "observations.csv").read_text()
    assert result.returncode == 0, result.stderr
    assert body.count("\n") == 3  # header + chainsafe's 2 functions
    assert TRUNCATED_NOTE in body


def test_truncation_is_named_in_the_log(tmp_path):
    """The 2026-09-18 run was cancelled and said nothing about it. A short night must announce
    itself, or the next person reads a thin day as a quiet one."""
    out = _cli(tmp_path, "chainsafe", "--deadline-minutes", "0").stdout
    assert "truncated" in out.lower()


def test_readings_persist_per_manifest_not_per_run(tmp_path, monkeypatch):
    """The 2026-09-18 failure in one line: 20 collected readings died with the process because
    nothing was written until the whole loop finished.

    Asserted by counting appends rather than by killing a subprocess mid-loop: a SIGKILL test
    would be timing-dependent, and the property that actually matters is that the store is
    written once per manifest, so at most one manifest's work is ever in flight.
    """
    import fpm.observations as _obs
    from fpm.cli import run_observe_cli

    # Two offline-measurable manifests. Only chainsafe.yaml has fixture responses, so the second
    # is a copy of it under another team name, in a registry dir of its own.
    registry = tmp_path / "registry"
    registry.mkdir()
    body = Path("tests/fixtures/chainsafe.yaml").read_text()
    (registry / "chainsafe.yaml").write_text(body)
    (registry / "zzz_second.yaml").write_text(
        body.replace("team: chainsafe", "team: zzz_second", 1)
    )

    calls = []
    real = _obs.append_observations

    def counting(observations, path, **kw):
        calls.append([o.team for o in observations])
        return real(observations, path, **kw)

    monkeypatch.setattr(_obs, "append_observations", counting)
    rc = run_observe_cli(
        teams=["chainsafe", "zzz_second"],
        registry_dir=str(registry),
        fixtures="fixtures/responses",
        as_of=datetime(2026, 8, 14, tzinfo=timezone.utc),
        method="nightly",
        csv_path=str(tmp_path / "observations.csv"),
        live_oso=False,
        oso_org="",
        dry_run=False,
        thresholds_csv=str(tmp_path / "thresholds.csv"),
    )
    assert rc == 0
    # One append per manifest, each carrying only that manifest's rows.
    assert len(calls) == 2
    assert [set(teams) for teams in calls] == [{"chainsafe"}, {"zzz_second"}]


def test_a_full_run_is_unchanged_without_a_deadline(tmp_path):
    result = _cli(tmp_path, "chainsafe")
    assert result.returncode == 0
    assert TRUNCATED_NOTE not in (tmp_path / "observations.csv").read_text()


def test_unattempted_metrics_are_kept_out_of_the_broken_source_diagnostic(tmp_path):
    """The "no value from N metrics" block groups blanks by host and hints at a credential, a
    rate limit or an outage. A metric nobody asked is none of those, and listing it there turns
    a short night into a false report of 41 broken endpoints."""
    out = _cli(tmp_path, "chainsafe", "--deadline-minutes", "0").stdout
    assert "TRUNCATED" in out
    assert "no value from" not in out
