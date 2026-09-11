"""Reconstructing the rolling release-average the registry actually commits to.

The trap this strategy exists to undo: `_release_series` emits `days_between_releases` -- the gap
since the previous release -- which is a DIFFERENT quantity from the registry's
`avg_days_between_releases`, joins to no commitment, and left 377 rows in the system of record
attached to nothing. So the tests here are mostly about computing the registry's formula, in the
registry's window, under the registry's name.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone

import pytest

UTC = timezone.utc


def _script():
    spec = importlib.util.spec_from_file_location("obs_rel", "scripts/observations.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["obs_rel"] = mod
    spec.loader.exec_module(mod)
    return mod


OBS = _script()
KEEP_ALL = OBS._RELEASE_AVG_FILTERS[""]
KEEP_STABLE = OBS._RELEASE_AVG_FILTERS[" WHERE tag_name LIKE 'v%' AND tag_name NOT LIKE '%-rc%'"]


def _rel(day: int, tag: str = "v1.0"):
    return {"tag_name": tag, "_dt": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day)}


def test_average_is_span_over_gaps_not_mean_of_gaps():
    """(max - min) / (n - 1), which is what the manifest's SQL computes."""
    rels = [_rel(0), _rel(10), _rel(40)]  # gaps of 10 and 30
    got = OBS.release_avg_at(rels, datetime(2026, 3, 1, tzinfo=UTC), 30, KEEP_ALL)
    assert got == pytest.approx(20.0)  # 40 days over 2 gaps


def test_only_releases_published_on_or_before_the_day_count():
    rels = [_rel(0), _rel(10), _rel(100)]
    asof = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=20)
    assert OBS.release_avg_at(rels, asof, 30, KEEP_ALL) == pytest.approx(10.0)


def test_the_window_is_the_newest_per_page_releases():
    """per_page bounds what the fetch returns, so it bounds what the average is over."""
    rels = [_rel(d) for d in (0, 100, 200, 300)]
    asof = datetime(2026, 12, 31, tzinfo=UTC)
    # newest 2 -> 200..300 -> 100 days over 1 gap
    assert OBS.release_avg_at(rels, asof, 2, KEEP_ALL) == pytest.approx(100.0)
    # all 4 -> 0..300 -> 300 days over 3 gaps
    assert OBS.release_avg_at(rels, asof, 30, KEEP_ALL) == pytest.approx(100.0)


def test_the_tag_filter_runs_AFTER_the_window_not_before():
    """dlt fetches `per_page` rows and the transform's WHERE runs on what came back. Filtering
    first would reach past releases the nightly never sees and report a different number."""
    rels = [_rel(0), _rel(10), _rel(20, "v1.1-rc1"), _rel(30, "v1.2-rc2")]
    asof = datetime(2026, 12, 31, tzinfo=UTC)
    # window = newest 2 = the two rc tags; both filtered out -> fewer than 2 left -> None
    assert OBS.release_avg_at(rels, asof, 2, KEEP_STABLE) is None
    # widen the window and the two stable ones survive
    assert OBS.release_avg_at(rels, asof, 4, KEEP_STABLE) == pytest.approx(10.0)


def test_fewer_than_two_releases_yields_no_value_rather_than_zero():
    """One release has no gap to average. A zero would read as 'ships constantly'."""
    rels = [_rel(0)]
    assert OBS.release_avg_at(rels, datetime(2026, 6, 1, tzinfo=UTC), 30, KEEP_ALL) is None
    assert OBS.release_avg_at([], datetime(2026, 6, 1, tzinfo=UTC), 30, KEEP_ALL) is None


def test_stable_filter_matches_the_lotus_predicate():
    assert KEEP_STABLE({"tag_name": "v1.33.0"})
    assert not KEEP_STABLE({"tag_name": "v1.33.0-rc1"})
    assert not KEEP_STABLE({"tag_name": "miner/v1.2.3"})


def test_targets_are_derived_from_the_registry_and_carry_its_metric_names():
    """A second hardcoded table would drift; these must be the registry's own names."""
    targets = OBS.release_avg_targets()
    by_fid = {t[1]: t for t in targets}
    assert by_fid["curio-sealing-release-cadence"][2] == "avg_days_between_releases"
    assert by_fid["libp2p-release-cadence"][2] == "libp2p_avg_days_between_releases"
    assert by_fid["lotus-consensus-client-release-cadence"][2] == "avg_days_between_stable_releases"
    # and never the neighbouring per-release-gap name that joins to nothing
    assert all(t[2] != "days_between_releases" for t in targets)


def test_every_target_metric_name_exists_in_the_registry():
    """The bug being fixed was a name that matched no commitment. Assert it cannot recur."""
    import pathlib

    from fpm.drafts import split_draft
    from fpm.manifest import load_manifest

    known = set()
    for p in sorted(pathlib.Path("registry").glob("*.yaml")):
        if p.name.startswith("_"):
            continue
        m = load_manifest(p)
        known |= {(m.team, f.function_id, f.sla.metric) for f in m.functions}
    for p in sorted(pathlib.Path("registry/drafts").glob("*.yaml")):
        m, _ = split_draft(p)
        known |= {(m.team, f.function_id, f.sla.metric) for f in m.functions}

    for team, fid, metric, *_ in OBS.release_avg_targets():
        assert (team, fid, metric) in known, f"{fid}/{metric} matches no registry commitment"


def test_an_unrecognized_transform_filter_raises_rather_than_being_ignored():
    """Silently dropping an unknown WHERE would compute a different metric under the right name."""
    assert " WHERE tag_name LIKE 'v%' AND tag_name NOT LIKE '%-rc%'" in OBS._RELEASE_AVG_FILTERS
    assert " WHERE something_else = 1" not in OBS._RELEASE_AVG_FILTERS


def test_release_cadence_is_not_in_the_default_rotation():
    """It emits a row per day per repo; a bare `backfill` must not add ~2,000 rows as a side effect."""
    assert "release-cadence" in OBS.TARGETED_ONLY
    assert "release-cadence" not in OBS.select_strategies(["releases", "release-cadence"], None)
