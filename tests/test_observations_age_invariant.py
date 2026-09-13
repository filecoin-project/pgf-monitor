"""The invariant holds over the COMMITTED series, not just tonight's write.

`fpm observe` refuses an impossible age reading before it is published (see
`tests/test_guards_age_growth.py`). That protects one write path. It does not protect
`data/observations.csv`, which is the system of record and is also written by
`scripts/observations.py backfill` -- a path that goes straight to `fpm.observations` and never
passes through the guard.

That gap is not hypothetical. The two false FDP readings were repaired by voiding the nightly and
recovering the true value under `backfill:api.github.com`; a backfill replaying a source that lies
the same way would put the same impossible number straight back, and nothing would notice. So the
history gets its own standing check, and it runs on every PR.
"""

from __future__ import annotations

import csv
import pathlib
from collections import defaultdict

from fpm.drafts import split_draft
from fpm.guards import age_growth_violation
from fpm.manifest import load_manifest

#: `derive` -> how many seconds one unit of the metric is worth.
_UNITS = {"age_seconds": 1.0, "age_days": 86400.0}


def age_metric_units() -> dict[tuple[str, str, str], float]:
    """Every age-shaped commitment in the registry, keyed the way the CSV is.

    Derived rather than listed, so a new age metric is covered the day it lands and a renamed one
    cannot quietly fall out of the check.
    """
    units: dict[tuple[str, str, str], float] = {}
    manifests = [
        load_manifest(p)
        for p in sorted(pathlib.Path("registry").glob("*.yaml"))
        if not p.name.startswith("_")
    ]
    manifests += [split_draft(p)[0] for p in sorted(pathlib.Path("registry/drafts").glob("*.yaml"))]
    for m in manifests:
        for f in m.functions:
            derive = str(getattr(f.source.extract, "derive", "")) if f.source.extract else ""
            if derive in _UNITS:
                units[(m.team, f.function_id, f.sla.metric)] = _UNITS[derive]
    return units


def test_the_registry_still_has_age_metrics_to_check():
    """A check over an empty set passes vacuously; make that failure loud instead."""
    assert len(age_metric_units()) >= 15


def test_no_committed_age_reading_outran_wall_time():
    units = age_metric_units()
    series = defaultdict(list)

    with pathlib.Path("data/observations.csv").open() as fh:
        for row in csv.DictReader(fh):
            key = (row["team"], row["function_id"], row["metric"])
            if key not in units or not row["observed_value"]:
                continue
            # Grouped by METHOD as well: a backfill row and a nightly row are two independent
            # observations of the same day, so comparing one against the other says nothing.
            series[(*key, row["method"])].append((row["observed_at"], float(row["observed_value"])))

    violations = []
    for (team, fid, metric, method), points in sorted(series.items()):
        points.sort()
        for (prev_day, prev_value), (day, value) in zip(points, points[1:]):
            reason = age_growth_violation(
                prev_value, prev_day, value, day, units[(team, fid, metric)]
            )
            if reason:
                violations.append(f"{team}/{metric} [{method}] {prev_day} -> {day}: {reason}")

    assert not violations, "impossible age readings in the system of record:\n" + "\n".join(
        violations
    )
