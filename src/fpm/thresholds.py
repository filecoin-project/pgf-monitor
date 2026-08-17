"""`data/thresholds.csv` — the commitment time series, and the system of record for it.

The sibling of fpm.observations, and deliberately shaped identically. Observations say what
was measured; this says what was promised on that same day. Compliance is the join, computed
where it is rendered rather than baked into either table.

The CSV is canonical: OSO's `filpgf_sla_thresholds` static model is a full-table republish of
this file, so a row is not real until it lands here and rides a commit. Git history is the
audit trail — a threshold cannot move silently, which is exactly what went wrong when the IPNI
bar sat at 0.95 for weeks against a signed 0.90.

One row per (observed_at, team, function_id, metric). `method` is deliberately NOT part of the
key: how a value was measured is a property of the measurement, not of the commitment.

Empty `threshold_op`/`threshold_value` means NO AGREED SLA — the function is measured but not
scored. That is a first-class state, not a gap to be filled in later with a guess.
"""

from __future__ import annotations

import csv
from pathlib import Path

CSV_PATH = Path("data/thresholds.csv")

COLUMNS = [
    "observed_at",
    "team",
    "function_id",
    "metric",
    "threshold_op",
    "threshold_value",
    "source",
]

Row = dict[str, str]


def normalize_date(value: object) -> str:
    """Truncate any ISO-8601 instant to its UTC date. `2026-08-16T06:17:00+00:00` -> `2026-08-16`.

    Deliberately naive, and identical to fpm.observations.normalize_date: the two tables are
    joined on this column, so they must truncate the same way or the join silently misses.
    """
    return str(value)[:10]


def row_key(row: Row) -> tuple[str, str, str, str]:
    return (
        normalize_date(row["observed_at"]),
        row["team"],
        row["function_id"],
        row["metric"],
    )


def to_row(rec) -> Row:
    value = rec.threshold_value
    return {
        "observed_at": normalize_date(rec.observed_at),
        "team": rec.team,
        "function_id": rec.function_id,
        "metric": rec.metric,
        "threshold_op": rec.threshold_op or "",
        "threshold_value": "" if value is None else repr(float(value)),
        "source": rec.source,
    }


def load_rows(path: Path = CSV_PATH) -> list[Row]:
    if not path.exists():
        return []
    with path.open() as f:
        return [{k: (v or "") for k, v in row.items() if k in COLUMNS} for row in csv.DictReader(f)]


def merge(existing: list[Row], new: list[Row]) -> list[Row]:
    """Fold new rows into existing ones. A new row REPLACES the old one on key collision.

    Last-wins makes a re-run idempotent: correcting a threshold and re-running the day should
    leave the day holding the corrected bar, not both.
    """
    merged: dict[tuple, Row] = {}
    for row in list(existing) + list(new):
        merged[row_key(row)] = {**row, "observed_at": normalize_date(row["observed_at"])}
    return sorted(
        merged.values(),
        key=lambda r: (r["team"], r["function_id"], r["metric"], r["observed_at"]),
    )


def save_rows(rows: list[Row], path: Path = CSV_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows([{c: row.get(c, "") for c in COLUMNS} for row in rows])


def append_thresholds(records: list, path: Path = CSV_PATH) -> list[Row]:
    """Merge threshold records into the CSV on disk and write it back. Returns the full table."""
    rows = merge(load_rows(path), [to_row(r) for r in records])
    save_rows(rows, path)
    return rows
