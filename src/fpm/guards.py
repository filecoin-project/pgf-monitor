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

from datetime import date

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
