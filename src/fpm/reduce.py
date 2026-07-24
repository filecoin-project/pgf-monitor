"""Collapse ingested rows to the single observed value the SLA evaluates."""

from __future__ import annotations

from datetime import datetime

from fpm.manifest import ExtractSpec


def _to_epoch(value: object, cast: str) -> float:
    """Cast a value to a float. `date` parses an ISO-8601 string (or passes a numeric epoch)."""
    if cast == "date" and not isinstance(value, (int, float)):
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    return float(value)


def reduce_rows(rows: list[dict], extract: ExtractSpec) -> float | None:
    col = extract.column
    if extract.reduce == "null_ratio":
        # fraction of ALL rows where the column is null or absent (e.g. error-free ratio)
        if not rows:
            return None
        nulls = sum(1 for r in rows if r.get(col) is None)
        return nulls / len(rows)
    present = [r for r in rows if col in r and r[col] is not None]
    if not present:
        return None
    if extract.reduce == "single":
        if len(present) != 1:
            return None
        return float(present[0][col])
    if extract.reduce == "latest":
        ts = extract.timestamp_column
        if not ts or any(ts not in r for r in present):
            return None
        latest = max(present, key=lambda r: r[ts])
        return float(latest[col])
    values = [float(r[col]) for r in present]
    if extract.reduce == "avg":
        return sum(values) / len(values)
    if extract.reduce == "min":
        return min(values)
    if extract.reduce == "max":
        return max(values)
    return None


def _select_row(rows: list[dict], extract: ExtractSpec) -> dict | None:
    """Pick the single target row for derive ops that need a whole row (single/latest)."""
    present = [r for r in rows if extract.column in r and r[extract.column] is not None]
    if not present:
        return None
    if extract.reduce == "single":
        return present[0] if len(present) == 1 else None
    if extract.reduce == "latest":
        ts = extract.timestamp_column
        if not ts or any(ts not in r for r in present):
            return None
        return max(present, key=lambda r: r[ts])
    return None


def derive_observed(
    rows: list[dict], extract: ExtractSpec, reference_time: datetime
) -> float | None:
    """Compute the observed value: a plain reduced value, a field difference, or an age.

    - value:       reduce_rows (single/latest/avg/min/max of `column`).
    - diff:        `column` - `column2` on the selected row (e.g. drand expected - current).
    - age_seconds: `reference_time` minus the Unix-seconds timestamp in `column` on the latest row.
      reference_time is the fetch time (now), never a historical as_of: freshness is now-relative.
    """
    if extract.derive == "value":
        return reduce_rows(rows, extract)
    row = _select_row(rows, extract)
    if row is None:
        return None
    if extract.derive == "diff":
        if not extract.column2 or extract.column2 not in row or row[extract.column2] is None:
            return None
        return _to_epoch(row[extract.column], extract.cast) - _to_epoch(
            row[extract.column2], extract.cast
        )
    if extract.derive in ("age_seconds", "age_days"):
        age_seconds = reference_time.timestamp() - _to_epoch(row[extract.column], extract.cast)
        return age_seconds / 86400 if extract.derive == "age_days" else age_seconds
    return None
