"""`data/observations.csv` — the append-only time series, and the system of record for it.

Measurement only: what a metric read as, on a given day. What that value is judged against is
a separate fact with its own time series (`fpm.thresholds`), because a threshold can be
corrected and a measurement cannot — compliance is computed by joining the two at render time,
never baked into this table.

The CSV is canonical: OSO's `filpgf_sla_observations` static model is a full-table republish of
this file, so a row is not real until it lands here and rides a commit. Git history is the audit
trail — a value cannot be revised silently.

One row per (observed_at, team, function_id, metric, method). `observed_at` is normalized to a
UTC date, so re-running a job on the same day updates that day's row instead of appending a
near-duplicate: the file has carried both `2026-07-19` and `2026-07-19T12:00:00+00:00` for the
same metric-day, which is exactly the bug that normalization closes.
"""

from __future__ import annotations

import csv
from pathlib import Path

from fpm.observe import Observation

CSV_PATH = Path("data/observations.csv")

COLUMNS = [
    "observed_at",
    "team",
    "function_id",
    "metric",
    "observed_value",
    "method",
    "note",
]

Row = dict[str, str]


def normalize_date(value: object) -> str:
    """Truncate any ISO-8601 instant to its UTC date. `2026-07-19T12:00:00+00:00` -> `2026-07-19`.

    Deliberately naive: every producer writes UTC, and a timezone-aware parse here would invent
    precision the sources do not have.
    """
    return str(value)[:10]


def row_key(row: Row) -> tuple[str, str, str, str, str]:
    return (
        normalize_date(row["observed_at"]),
        row["team"],
        row["function_id"],
        row["metric"],
        row["method"],
    )


def to_row(obs: Observation) -> Row:
    value = obs.observed_value
    return {
        "observed_at": normalize_date(obs.observed_at),
        "team": obs.team,
        "function_id": obs.function_id,
        "metric": obs.metric,
        "observed_value": "" if value is None else repr(float(value)),
        "method": obs.method,
        "note": obs.note,
    }


def load_rows(path: Path = CSV_PATH) -> list[Row]:
    if not path.exists():
        return []
    with path.open() as f:
        return [{k: (v or "") for k, v in row.items() if k in COLUMNS} for row in csv.DictReader(f)]


def merge(existing: list[Row], new: list[Row]) -> list[Row]:
    """Fold new rows into existing ones. A new row REPLACES the old one on key collision.

    Last-wins is what makes a re-run idempotent and self-healing: if the 06:00 run went
    indeterminate because an endpoint was down and someone re-runs at noon, the day should end up
    holding the good reading, not the first one recorded.
    """
    merged: dict[tuple, Row] = {}
    for row in list(existing) + list(new):
        merged[row_key(row)] = {**row, "observed_at": normalize_date(row["observed_at"])}
    return sorted(
        merged.values(),
        key=lambda r: (r["team"], r["function_id"], r["metric"], r["observed_at"], r["method"]),
    )


def save_rows(rows: list[Row], path: Path = CSV_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows([{c: row.get(c, "") for c in COLUMNS} for row in rows])


def collection_status(rows: list[Row], day: str) -> tuple[int, int]:
    """(rows recorded, rows carrying a value) for one day.

    A day where the pipeline recorded readings and NOT ONE of them carries a value is not a
    quiet night; it is the instrument being broken. That state held from 2026-08-22 to
    2026-08-24 -- OSO had changed the ingestion-trigger payload, every fetch raised, and the
    nightly workflow reported success three times because a per-function fetch failure is
    isolated by design. Nothing distinguished it from a night when every source was simply
    healthy and quiet. This is what does.
    """
    d = normalize_date(day)
    todays = [r for r in rows if normalize_date(r["observed_at"]) == d]
    carried = sum(1 for r in todays if str(r.get("observed_value") or "").strip() != "")
    return len(todays), carried


def append_observations(observations: list[Observation], path: Path = CSV_PATH) -> list[Row]:
    """Merge observations into the CSV on disk and write it back. Returns the full table."""
    rows = merge(load_rows(path), [to_row(o) for o in observations])
    save_rows(rows, path)
    return rows
