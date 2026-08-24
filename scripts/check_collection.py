"""The blackout guard: fail when a day's readings carry no value at all.

Runs LAST in `.github/workflows/observe.yml` -- after the commit and after the republish -- on
purpose. A night where every metric came back value-less is an infrastructure failure and must
turn the workflow red, but the record of that night is itself evidence and belongs in git and in
the warehouse. Folding this into `fpm observe`'s exit code would abort the job before the commit
step and throw the evidence away, so it is a separate assertion at the end.

`fpm observe` deliberately isolates a per-function fetch failure so one broken source cannot
abort the run (fpm.observe.measure). The cost of that design is that a failure hitting EVERY
function looks identical to a successful run. This is the check that tells them apart.

Usage:
    uv run python -m scripts.check_collection [--as-of YYYY-MM-DD] [--csv PATH]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from fpm.observations import CSV_PATH, collection_status, load_rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--as-of", default="", help="day to check (YYYY-MM-DD, default today UTC)")
    ap.add_argument("--csv", default=str(CSV_PATH), help="observations CSV")
    args = ap.parse_args(argv)

    day = args.as_of or datetime.now(timezone.utc).date().isoformat()
    recorded, carried = collection_status(load_rows(Path(args.csv)), day)

    if recorded == 0:
        print(
            f"::error::no readings at all were recorded for {day} — the observation run did not "
            f"reach the store",
            file=sys.stderr,
        )
        return 1
    if carried == 0:
        print(
            f"::error::all {recorded} readings recorded for {day} are value-less. That is the "
            f"instrument, not the sources: check the `note` column in data/observations.csv — a "
            f"single repeated error across every metric means one shared failure (the OSO API, a "
            f"credential, egress), not {recorded} broken endpoints",
            file=sys.stderr,
        )
        return 1

    print(f"{day}: {carried} of {recorded} readings carry a value")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
