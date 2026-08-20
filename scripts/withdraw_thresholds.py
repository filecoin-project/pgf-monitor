"""Withdraw a bar across the whole threshold series, so history is judged by what was agreed.

`data/thresholds.csv` records the bar as it stood on each day, and the dashboard derives compliance
by joining it to the reading for that day. That design exists so a bar can be CORRECTED: fixing a
row re-judges history instead of leaving old readings measured against a number nobody agreed to.
This is the tool that does the fixing.

Withdrawing (rather than deleting) keeps the daily row and blanks `threshold_op` / `threshold_value`,
which is exactly the shape `fpm.thresholds` writes for an unscored metric. So a withdrawn day is
indistinguishable from a day the registry carried no bar -- which is the point, because that is what
was true. The rows stay so the record still shows the metric was tracked that day.

  uv run python scripts/withdraw_thresholds.py --all --dry-run
  uv run python scripts/withdraw_thresholds.py --all
  uv run python scripts/withdraw_thresholds.py --metric plumbline/calibnet-sp-power-share

Observations are never touched: a measurement cannot be corrected, only a commitment can. Writes go
through `fpm.thresholds.save_rows`, never a hand-rolled CSV write.
"""

from __future__ import annotations

import argparse

from fpm.thresholds import CSV_PATH, load_rows, save_rows


def withdraw(rows: list[dict], selectors: set[str] | None) -> tuple[list[dict], int]:
    """Blank op/value on every row selected. `None` selects every row.

    A selector is `team/function_id`, which is a commitment's identity; the metric name rides along
    rather than being part of the key, because one function reports exactly one metric.
    """
    changed = 0
    out = []
    for row in rows:
        key = f"{row['team']}/{row['function_id']}"
        hit = selectors is None or key in selectors
        if hit and (row.get("threshold_op") or row.get("threshold_value")):
            row = {**row, "threshold_op": "", "threshold_value": ""}
            changed += 1
        out.append(row)
    return out, changed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="withdraw_thresholds")
    ap.add_argument(
        "--metric",
        action="append",
        default=[],
        metavar="TEAM/FUNCTION_ID",
        help="withdraw one commitment's bar across all days; repeatable",
    )
    ap.add_argument("--all", action="store_true", help="withdraw every bar in the series")
    ap.add_argument(
        "--dry-run", action="store_true", help="report what would change, write nothing"
    )
    args = ap.parse_args(argv)
    if bool(args.metric) == bool(args.all):
        ap.error("pass either --all or one or more --metric, not both and not neither")

    rows = load_rows(CSV_PATH)
    selectors = None if args.all else set(args.metric)
    if selectors is not None:
        known = {f"{r['team']}/{r['function_id']}" for r in rows}
        for missing in sorted(selectors - known):
            # Silently withdrawing nothing would read as success; name it instead.
            print(f"WARNING {missing} appears nowhere in {CSV_PATH}")
    updated, changed = withdraw(rows, selectors)
    affected = sorted(
        {
            f"{r['team']}/{r['metric']}"
            for r, u in zip(rows, updated)
            if r.get("threshold_op") and not u.get("threshold_op")
        }
    )
    print(f"{changed} row(s) across {len(affected)} metric(s) would lose their bar:")
    for a in affected:
        print(f"  {a}")
    if args.dry_run:
        print("dry run: nothing written")
        return 0
    save_rows(updated, CSV_PATH)
    print(f"{CSV_PATH}: {len(updated)} rows, {changed} withdrawn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
