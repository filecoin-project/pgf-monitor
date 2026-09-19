"""Re-running a night must not refuse the readings it takes.

The age guard compares today's reading against the last recorded one and refuses growth that
outruns wall time. `previous` is meant to be "the series as it stood BEFORE tonight" -- the
comment in `run_observe_cli` says exactly that -- but it was built from the last row per
commitment including a row dated TODAY. So a second run on a day that already has readings
compared today against today: zero days elapsed, only the 0.5d scheduler-jitter budget allowed,
and any real growth beyond it refused, nulled and written to the evidence directory.

Found 2026-09-19 by a live rehearsal, not by a test. `zondax/rosetta_release_age_days` read
73.48835 at the 05:23 nightly and 74.0465 at 19:12 -- +0.558d over 13.8h of real elapsed time,
which is the source being exactly right -- and the guard threw it away.

Why it matters more since #83: a truncated night now turns `check_collection` red, which invites
an operator to re-run the night. That is the precise action this tripped on. The normal
once-a-day nightly never hit it, which is why a year of them did not surface it.
"""

from datetime import datetime, timezone
from pathlib import Path

from fpm.cli import previous_readings

AS_OF = datetime(2026, 9, 19, tzinfo=timezone.utc)

HEADER = "observed_at,team,function_id,metric,observed_value,method,note\n"


def _csv(tmp_path: Path, *rows: str) -> Path:
    p = tmp_path / "observations.csv"
    p.write_text(HEADER + "".join(r + "\n" for r in rows))
    return p


def test_a_reading_from_today_is_not_used_as_its_own_comparison_point(tmp_path):
    """The whole bug, in one assertion."""
    p = _csv(
        tmp_path,
        "2026-09-18,zondax,rosetta-release-currency,rosetta_release_age_days,72.5,nightly,",
        "2026-09-19,zondax,rosetta-release-currency,rosetta_release_age_days,73.488,nightly,",
    )
    prev = previous_readings(p, AS_OF)
    day, value = prev[("zondax", "rosetta-release-currency", "rosetta_release_age_days")]
    assert day == "2026-09-18"
    assert value == 72.5


def test_the_last_prior_day_wins_not_merely_the_last_row(tmp_path):
    """Rows are not ordered in the file, and a backfill can land after a later nightly."""
    p = _csv(
        tmp_path,
        "2026-09-17,t,f,m,10.0,nightly,",
        "2026-09-19,t,f,m,99.0,nightly,",
        "2026-09-18,t,f,m,20.0,backfill:api.github.com,",
    )
    assert previous_readings(p, AS_OF)[("t", "f", "m")] == ("2026-09-18", 20.0)


def test_a_commitment_whose_only_reading_is_today_has_no_comparison_point(tmp_path):
    """No prior day means no guard, which is the right default -- the same as a first-ever run.
    Inventing one from today's own row is what produced the false refusal."""
    p = _csv(tmp_path, "2026-09-19,t,f,m,5.0,nightly,")
    assert ("t", "f", "m") not in previous_readings(p, AS_OF)


def test_value_less_rows_are_still_skipped(tmp_path):
    """Pre-existing behaviour, kept: a null carries no comparison point."""
    p = _csv(
        tmp_path,
        "2026-09-16,t,f,m,7.0,nightly,",
        "2026-09-17,t,f,m,,nightly,fetch_error: boom",
    )
    assert previous_readings(p, AS_OF)[("t", "f", "m")] == ("2026-09-16", 7.0)


def test_a_missing_file_yields_no_comparison_points(tmp_path):
    assert previous_readings(tmp_path / "nope.csv", AS_OF) == {}


def test_the_real_refusal_from_2026_09_19_no_longer_happens(tmp_path):
    """End to end against `apply_age_guard`, with the actual numbers from the rehearsal."""
    from fpm.manifest import load_manifest
    from fpm.observe import Observation, apply_age_guard

    p = _csv(
        tmp_path,
        "2026-09-17,zondax,rosetta-release-currency,rosetta_release_age_days,71.48943,nightly,",
        "2026-09-19,zondax,rosetta-release-currency,rosetta_release_age_days,73.48835,nightly,",
    )
    fn = next(
        f
        for f in load_manifest("registry/zondax.yaml").functions
        if f.function_id == "rosetta-release-currency"
    )
    obs = Observation(
        observed_at="2026-09-19",
        team="zondax",
        function_id="rosetta-release-currency",
        metric="rosetta_release_age_days",
        observed_value=74.0465,  # read 13.8h after the 05:23 nightly; correct, and refused
        method="nightly",
    )
    apply_age_guard(fn, obs, previous_readings(p, AS_OF))
    assert obs.observed_value == 74.0465, "a same-day re-run must not null a correct reading"
    assert "impossible age growth" not in obs.note
