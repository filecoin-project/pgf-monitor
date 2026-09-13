"""The one reading this system refuses to publish: an age that outran wall time.

Twice now `pipeline_success_age_days` has reported the Filecoin Data Portal's pipeline as weeks
stale while it ran successfully every night — 36/37/38 days in August, 12.63 and 17.63 in
September. The cause is upstream and not reproducible on demand. What is in our control is
declining to republish a number we can prove false about a funded data project.
"""

from __future__ import annotations


from fpm.guards import age_growth_violation
from fpm.manifest import ExtractSpec, FunctionSpec, SlaSpec, SourceSpec
from fpm.observe import Observation, apply_age_guard


# --- the pure invariant ---------------------------------------------------------------------


def test_the_real_2026_09_13_reading_is_refused():
    """0.5102 -> 17.6292 overnight. The number that would have accused FDP of five weeks stale."""
    reason = age_growth_violation(0.5102, "2026-09-12", 17.6292, "2026-09-13")
    assert reason is not None
    assert "impossible age growth" in reason and "17.12 days" in reason


def test_the_august_episode_is_refused_too():
    reason = age_growth_violation(0.669, "2026-08-25", 36.63, "2026-08-26")
    assert reason is not None


def test_a_normal_days_growth_passes():
    assert age_growth_violation(0.5102, "2026-09-12", 0.5489, "2026-09-13") is None


def test_a_clock_reset_is_always_allowed():
    """A fall is the healthy event — the thing being watched happened again."""
    assert age_growth_violation(38.74, "2026-08-28", 0.2671, "2026-08-29") is None


def test_growth_up_to_elapsed_time_is_allowed():
    """A genuinely stale source must still be reportable: 3 days of silence reads as +3 days."""
    assert age_growth_violation(1.0, "2026-09-01", 4.0, "2026-09-04") is None


def test_a_gap_in_the_series_widens_the_budget():
    """After a 10-day gap, a 10-day growth is truthful, not impossible."""
    assert age_growth_violation(1.0, "2026-09-01", 11.0, "2026-09-11") is None
    assert age_growth_violation(1.0, "2026-09-01", 25.0, "2026-09-11") is not None


def test_scheduler_jitter_does_not_trip_it():
    """The nightly has fired up to ~9 minutes late; the tolerance must swallow that."""
    assert age_growth_violation(0.50, "2026-09-12", 1.40, "2026-09-13") is None


def test_age_seconds_metrics_are_converted_before_comparing():
    """A 12-day jump expressed in SECONDS must trip the same rule."""
    twelve_days = 12 * 86400.0
    assert age_growth_violation(600.0, "2026-09-12", twelve_days, "2026-09-13", 1.0) is not None
    assert age_growth_violation(600.0, "2026-09-12", 900.0, "2026-09-13", 1.0) is None


def test_out_of_order_days_are_not_this_guards_business():
    assert age_growth_violation(1.0, "2026-09-13", 50.0, "2026-09-12") is None


# --- the wiring into an observation -----------------------------------------------------------


def _fn(derive="age_days"):
    return FunctionSpec(
        function_id="network-data-portal-pipeline-freshness",
        tier="essential",
        sla=SlaSpec(statement="s", metric="pipeline_success_age_days", cadence="daily"),
        source=SourceSpec(
            adapter="oso",
            kind="http-json",
            extract=ExtractSpec(column="created_at", derive=derive),
        ),
    )


def _obs(value):
    return Observation(
        observed_at="2026-09-13",
        team="filecoin-data-portal",
        function_id="network-data-portal-pipeline-freshness",
        metric="pipeline_success_age_days",
        observed_value=value,
        method="nightly",
    )


KEY = (
    "filecoin-data-portal",
    "network-data-portal-pipeline-freshness",
    "pipeline_success_age_days",
)


def test_a_false_reading_is_nulled_and_says_why():
    obs = _obs(17.6292)
    apply_age_guard(_fn(), obs, {KEY: ("2026-09-12", 0.5102)})
    assert obs.observed_value is None
    assert obs.outcome == "indeterminate"
    assert "impossible age growth" in obs.note


def test_a_good_reading_is_left_alone():
    obs = _obs(0.5489)
    apply_age_guard(_fn(), obs, {KEY: ("2026-09-12", 0.5102)})
    assert obs.observed_value == 0.5489
    assert obs.note == ""


def test_no_history_means_no_guard():
    """A first reading has nothing to contradict, and must not be suppressed for it."""
    obs = _obs(17.6292)
    apply_age_guard(_fn(), obs, {})
    assert obs.observed_value == 17.6292


def test_non_age_metrics_are_untouched():
    """A count or a balance may legitimately jump by any amount overnight."""
    fn = _fn(derive="value")
    obs = _obs(5000.0)
    apply_age_guard(fn, obs, {KEY: ("2026-09-12", 1.0)})
    assert obs.observed_value == 5000.0


def test_an_already_null_reading_is_untouched():
    obs = _obs(None)
    apply_age_guard(_fn(), obs, {KEY: ("2026-09-12", 0.5)})
    assert obs.observed_value is None
    assert obs.note == ""


def test_the_whole_registry_is_scanned_not_just_fdp():
    """The guard keys off `derive: age_*`, so it covers every age metric, not one hardcoded id."""
    import pathlib

    from fpm.drafts import split_draft
    from fpm.manifest import load_manifest

    adopted = drafts = 0
    for p in sorted(pathlib.Path("registry").glob("*.yaml")):
        if p.name.startswith("_"):
            continue
        for f in load_manifest(p).functions:
            if f.source.extract and str(f.source.extract.derive).startswith("age_"):
                adopted += 1
    for p in sorted(pathlib.Path("registry/drafts").glob("*.yaml")):
        for f in split_draft(p)[0].functions:
            if f.source.extract and str(f.source.extract.derive).startswith("age_"):
                drafts += 1
    # 6 adopted + 10 draft as of 2026-09-13. The point is that the guard protects a FAMILY, not
    # the one metric that exposed the fault, so a shrinking count is worth noticing.
    assert adopted >= 5, f"only {adopted} adopted age metrics; has the family shrunk?"
    assert adopted + drafts >= 12
