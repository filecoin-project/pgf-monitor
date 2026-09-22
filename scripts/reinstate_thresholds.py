"""Reinstate a bar across the threshold series, from the day its agreement was executed.

The mirror of `withdraw_thresholds.py`. `data/thresholds.csv` records the bar as it stood on each
day and the dashboard derives compliance by joining it to that day's reading, so putting a number
back re-judges history rather than leaving readings permanently unscored. That is the mechanism the
2026-08-20 withdrawal relied on: "when contracts are signed the bars return unchanged".

A bar is reinstated FROM A DATE, not across the whole series, because a team is accountable from
the day it signed and not before. Rows before that date keep their blank op/value, which is the
same shape an unscored metric writes -- and which is what was true.

  uv run python scripts/reinstate_thresholds.py --from-registry --dry-run
  uv run python scripts/reinstate_thresholds.py --from-registry

Execution dates come from `--executed TEAM=YYYY-MM-DD`, read off the signature block of each
executed agreement. A team with a bar in the registry but no execution date is refused rather than
backdated to the beginning of the series. Observations are never touched: a measurement cannot be
corrected, only a commitment can. Writes go through `fpm.thresholds.save_rows`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fpm.manifest import load_manifest
from fpm.thresholds import CSV_PATH, load_rows, save_rows


def registry_bars(registry_dir: str) -> dict[tuple[str, str], tuple[str, str]]:
    """(team, function_id) -> (op, value) for every commitment the registry now scores."""
    bars: dict[tuple[str, str], tuple[str, str]] = {}
    for path in sorted(Path(registry_dir).glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        manifest = load_manifest(path)
        for fn in manifest.functions:
            if fn.sla.threshold_op and fn.sla.threshold_value is not None:
                value = fn.sla.threshold_value
                rendered = str(int(value)) if float(value).is_integer() else str(value)
                bars[(manifest.team, fn.function_id)] = (fn.sla.threshold_op, rendered)
    return bars


def reinstate(rows, bars, executed):
    changed, skipped_no_date = 0, set()
    out = []
    for row in rows:
        key = (row["team"], row["function_id"])
        bar = bars.get(key)
        if not bar:
            out.append(row)
            continue
        on = executed.get(row["team"])
        if not on:
            skipped_no_date.add(row["team"])
            out.append(row)
            continue
        if row["observed_at"] >= on and not row.get("threshold_op"):
            op, value = bar
            row = {**row, "threshold_op": op, "threshold_value": value}
            changed += 1
        out.append(row)
    return out, changed, skipped_no_date


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="reinstate_thresholds")
    ap.add_argument("--registry", default="registry", help="registry directory")
    ap.add_argument(
        "--executed",
        action="append",
        default=[],
        metavar="TEAM=YYYY-MM-DD",
        help="the date that team's agreement was executed; repeatable",
    )
    ap.add_argument("--from-registry", action="store_true", help="reinstate every scored bar")
    ap.add_argument("--dry-run", action="store_true", help="report, write nothing")
    args = ap.parse_args(argv)

    executed = dict(pair.split("=", 1) for pair in args.executed)
    bars = registry_bars(args.registry)
    rows = load_rows(CSV_PATH)
    updated, changed, missing = reinstate(rows, bars, executed)

    per_metric: dict[str, int] = {}
    for before, after in zip(rows, updated):
        if not before.get("threshold_op") and after.get("threshold_op"):
            per_metric[f"{after['team']}/{after['metric']}"] = (
                per_metric.get(f"{after['team']}/{after['metric']}", 0) + 1
            )
    print(f"{changed} row(s) across {len(per_metric)} metric(s) would regain a bar:")
    for name in sorted(per_metric):
        print(f"  {name}: {per_metric[name]} day(s)")
    for team in sorted(missing):
        print(f"REFUSED {team}: scored in the registry but no --executed date given")
    if args.dry_run:
        print("dry run: nothing written")
        return 0
    if missing:
        print("nothing written: supply an execution date for every scored team")
        return 1
    save_rows(updated, CSV_PATH)
    print(f"{CSV_PATH}: {len(updated)} rows, {changed} reinstated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
