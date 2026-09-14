"""Readings we can prove are false, refused before they are published.

This is not threshold judgement and not adjudication — both of those are a human's job. It is the
narrower case where a reading contradicts arithmetic, so publishing it would assert something that
cannot be true of the thing being measured.

Only one such invariant exists today, and it earned its place the hard way. An AGE metric — "how
long since the last successful run / commit / snapshot" — can reset to zero whenever the thing it
watches happens again, but it can only GROW by at most the wall-clock time that has passed. A
freshness clock that gains twelve days overnight is not a stale pipeline; it is a bad reading.

That exact failure has now hit `filecoin-data-portal/pipeline_success_age_days` twice. On
2026-08-26/27/28 it published 36.63, 37.73 and 38.74 days while the pipeline ran successfully every
one of those days, then healed unaided. On 2026-09-08 it published 12.63 and on 2026-09-13 17.63,
both measured against a stale set of runs whose newest was 2026-08-26T14:36Z, while GitHub's API
returned the correct recent runs to every manual request. The cause is upstream and not
reproducible on demand; what IS in our control is not republishing the claim.

A null is honest here, and the repo already takes that position for a reading proven wrong
(`scripts/observations.py void`). It says the day has no defensible number, which is exactly true.
Inventing a replacement would be worse, and publishing 17.63 says a funded data project let its
pipeline go five weeks stale — a false accusation, rendered on a public page, about the very thing
that project exists to do well.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

#: Wall-clock tolerance, in days. The nightly does not fire at a fixed instant — GitHub Actions
#: has started it up to ~9 minutes late — so two consecutive readings can legitimately sit slightly
#: more than 24h apart. Half a day is far wider than that jitter and far narrower than any real
#: instance of this fault, all of which have overshot by 12 days or more.
AGE_GROWTH_TOLERANCE_DAYS = 0.5


def age_growth_violation(
    previous_value: float,
    previous_day: str,
    value: float,
    day: str,
    unit_seconds: float = 86400.0,
) -> str | None:
    """Reason string when an age reading grew faster than time did, else None.

    `unit_seconds` converts the metric's own unit into days — 86400 for an `age_days` metric,
    1 for `age_seconds`. Both shapes exist in the registry.

    A FALL is always allowed and never flagged: that is the clock resetting, which is the normal
    healthy event for every one of these metrics.
    """
    elapsed = (date.fromisoformat(day) - date.fromisoformat(previous_day)).days
    if elapsed < 0:
        return None  # out-of-order write; not this guard's business
    growth_days = (value - previous_value) * (unit_seconds / 86400.0)
    budget = elapsed + AGE_GROWTH_TOLERANCE_DAYS
    if growth_days <= budget:
        return None
    return (
        f"impossible age growth: {previous_value:g} -> {value:g} is +{growth_days:.2f} days "
        f"across {elapsed} day(s) elapsed. An age clock can reset but cannot outrun wall time, "
        f"so this reading is false rather than alarming; nulled instead of published"
    )


#: Where a refused reading's evidence is written. Deliberately NOT under `data/` — that directory
#: is the published system of record and `observe.yml` commits an explicit pathspec of CSVs from
#: it. A capture is diagnostic material for us, not a published fact, so it stays out of git and
#: rides out of CI as a workflow artifact instead.
CAPTURE_DIR_ENV = "FPM_GUARD_CAPTURE_DIR"
DEFAULT_CAPTURE_DIR = Path("evidence/refused-readings")

#: A refused reading is rare and its rows are a handful; a runaway source should not be able to
#: write an unbounded file into CI.
MAX_CAPTURED_ROWS = 200


def capture_dir(explicit: str | Path | None = None) -> Path:
    if explicit is not None:
        return Path(explicit)
    return Path(os.environ.get(CAPTURE_DIR_ENV) or DEFAULT_CAPTURE_DIR)


def capture_refused_reading(
    *,
    team: str,
    function_id: str,
    metric: str,
    observed_at: str,
    refused_value: float,
    previous_day: str,
    previous_value: float,
    reason: str,
    reading: Any = None,
    directory: str | Path | None = None,
    endpoint: str = "",
) -> Path | None:
    """Preserve what produced a reading the guard refused. Returns the file written, or None.

    Refusing the reading is the right call and it is also the only sample we will ever get. The
    fault behind `pipeline_success_age_days` has now fired four times across three weeks and was
    never root-caused, because by the time anyone looked the ingestion table had been overwritten
    (`write_disposition: replace`) and the run logs had aged out. Nulling the value and moving on
    throws away the evidence at the exact moment it exists.

    What matters most here is NOT the rows -- it is `oso_run_ref`. Those identifiers are what let
    someone ask OSO what its ingestion actually did that night, which is the question the
    investigation could not answer: whether GitHub served a bad response, or whether something
    between GitHub and the table produced one. The rows alone cannot separate those.

    Never raises. A capture is a diagnostic nicety; failing to write one must not take down a
    night's collection or turn a refused reading into a crashed run.
    """
    try:
        target = capture_dir(directory)
        target.mkdir(parents=True, exist_ok=True)
        rows = list(getattr(reading, "raw_rows", None) or [])
        claim = getattr(reading, "claim", None)
        evidence = getattr(claim, "evidence", None)
        run_ref = getattr(evidence, "oso_run_ref", None)
        record = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "observed_at": observed_at,
            "team": team,
            "function_id": function_id,
            "metric": metric,
            "refused_value": refused_value,
            "previous_day": previous_day,
            "previous_value": previous_value,
            # The handle on OSO's side of the fetch. This is the point of the whole exercise.
            "oso_run_ref": run_ref.model_dump(mode="json") if run_ref is not None else None,
            # Already secret-stripped where it is built; see the fingerprint note in CLAUDE.md.
            "request_fingerprint": getattr(evidence, "request_fingerprint", None),
            "source_ref": getattr(claim, "source_ref", None),
            # The exact URL asked for, so `scripts/capture_control_fetch.py` can repeat the
            # request directly and record what GitHub says to US at the same moment.
            "endpoint": endpoint,
            "source_metadata": getattr(reading, "source_metadata", None),
            "row_count": len(rows),
            "rows_truncated": len(rows) > MAX_CAPTURED_ROWS,
            "rows": rows[:MAX_CAPTURED_ROWS],
        }
        path = target / f"{observed_at}_{team}_{metric}.json"
        path.write_text(json.dumps(record, indent=2, default=str) + "\n")
        return path
    except Exception:
        return None
