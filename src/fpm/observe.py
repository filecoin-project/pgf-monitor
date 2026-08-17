"""The deterministic half of the pipeline: fetch a source, evaluate the SLA, stop.

`run_review` adds inference and human adjudication on top of this; a scheduled observation run
must not, because there is nobody at the keyboard to adjudicate and a nightly LLM narrative would
be a nondeterministic artifact nobody asked for. Both paths call `measure`, so the number a
reviewer adjudicates and the number the time series records can never drift apart.

An Observation is one row of `data/observations.csv` — see fpm.observations for the store.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from pydantic import Field

from fpm.adapters.base import Adapter
from fpm.adapters.registry import UnsupportedAdapterError, build_adapters
from fpm.domain import (
    Claim,
    ComparisonOperator,
    MeasurementWindow,
    Reading,
    SlaOutcome,
    SlaResult,
    _Model,
    window_for,
)
from fpm.evaluate import evaluate_sla
from fpm.manifest import FunctionSpec, Manifest, load_manifest


class Observation(_Model):
    """One (day, team, function, metric) reading, flattened for the CSV time series.

    Measurement only. What the value was judged against is a separate fact with its own
    time series (fpm.thresholds), because a threshold can be corrected and a measurement
    cannot.
    """

    observed_at: str  # YYYY-MM-DD, UTC
    team: str
    function_id: str
    metric: str
    observed_value: float | None
    method: str
    note: str = ""
    # Reported in the run log, deliberately NOT a CSV column: this is operator feedback about
    # today's run, not a fact about the reading. `exclude=True` keeps it out of any dump.
    outcome: SlaOutcome = Field(default="indeterminate", exclude=True)


class ThresholdRecord(_Model):
    """One (day, team, function, metric) commitment, flattened for the CSV time series.

    Separate from Observation on purpose: a value and a promise are different kinds of fact,
    and only one of them changes when a grant agreement is corrected.
    """

    observed_at: str  # YYYY-MM-DD, UTC
    team: str
    function_id: str
    metric: str
    threshold_op: ComparisonOperator | None
    threshold_value: float | None
    source: str


def error_reading(
    fn: FunctionSpec, team: str, window: MeasurementWindow, exc: Exception
) -> Reading:
    """A value-less reading standing in for a function whose fetch raised, so the batch continues.

    evaluate_sla turns the absent value into `indeterminate`; the error is preserved in
    source_metadata for the human adjudicator. Mirrors how a failed ingestion run is handled.
    """
    return Reading(
        team=team,
        function_id=fn.function_id,
        metric=fn.sla.metric,
        measurement_window=window,
        claim=Claim(
            value=None,
            origin="independent",
            source_ref=fn.source.base_url,
            fetched_at=datetime.now(timezone.utc),
            evidence=None,
            fetched_by="pipeline",
        ),
        source_metadata={"fetch_error": str(exc)},
        adapter=fn.source.adapter,
        adapter_version="error",
    )


def measure(
    fn: FunctionSpec,
    team: str,
    adapters: dict[str, Adapter],
    as_of: datetime,
) -> tuple[Adapter, Reading, SlaResult]:
    """Fetch one function and evaluate its SLA. Never raises for a source-side failure."""
    adapter = adapters[fn.source.adapter]
    if adapter.name != fn.source.adapter:  # defensive: registry contract
        raise UnsupportedAdapterError(fn.source.adapter)
    window = window_for(fn.sla.cadence, as_of)
    try:
        reading = adapter.fetch(fn, team, window)
    except Exception as exc:
        # Isolate a single function's fetch failure (egress block, network, API error) so it does
        # not abort the whole run. The value-less reading yields an indeterminate outcome with the
        # error recorded, and the remaining functions still run.
        reading = error_reading(fn, team, window, exc)
    return adapter, reading, evaluate_sla(reading, fn, team)


def _note(reading: Reading, sla: SlaResult) -> str:
    """Why a reading is what it is — the failure cause when there is one, else empty."""
    meta = reading.source_metadata
    for key in ("fetch_error", "transform_error"):
        if meta.get(key):
            return f"{key}: {meta[key]}"
    # A failed ingestion run leaves no rows, which then reads as "no value in source response" —
    # blaming the source for what was actually a fetch that never completed. Say which it was:
    # that distinction is the difference between "this API changed" and "our request was rejected".
    status = meta.get("run_status")
    if sla.outcome == "indeterminate" and status and status != "SUCCESS":
        return f"ingestion run {status}: {sla.reason}"
    return sla.reason if sla.outcome == "indeterminate" else ""


def to_observation(
    fn: FunctionSpec, team: str, reading: Reading, sla: SlaResult, as_of: datetime, method: str
) -> Observation:
    return Observation(
        observed_at=as_of.date().isoformat(),
        team=team,
        function_id=fn.function_id,
        metric=fn.sla.metric,
        observed_value=sla.observed,
        method=method,
        note=_note(reading, sla),
        outcome=sla.outcome,
    )


def observe(
    manifest_path: str | Path,
    fixtures_dir: Path,
    as_of: datetime,
    method: str = "nightly",
    oso_client=None,
    org_id: str = "",
    allowlist: set[str] | None = None,
    poll_sleep: float = 0.0,
    on_observation: Callable[[Observation], None] | None = None,
) -> list[Observation]:
    """Measure every function in one manifest. One Observation per function, always.

    `on_observation` fires as each metric lands, so a caller can report progress during a run
    that takes tens of minutes rather than only at the end.
    """
    manifest: Manifest = load_manifest(manifest_path)
    adapters = build_adapters(
        fixtures_dir,
        oso_client=oso_client,
        org_id=org_id,
        allowlist=allowlist,
        poll_sleep=poll_sleep,
    )
    out = []
    for fn in manifest.functions:
        _, reading, sla = measure(fn, manifest.team, adapters, as_of)
        obs = to_observation(fn, manifest.team, reading, sla, as_of, method)
        out.append(obs)
        if on_observation is not None:
            on_observation(obs)
    return out


def thresholds_for(manifest_path: str | Path, as_of: datetime) -> list[ThresholdRecord]:
    """The commitments a manifest declares on one day. Pure: no adapters, no network.

    Emits a row for EVERY function, including ones with no agreed threshold — the absence is
    the fact being recorded, and a missing row would be indistinguishable from a day the
    monitor did not run.
    """
    manifest: Manifest = load_manifest(manifest_path)
    day = as_of.date().isoformat()
    return [
        ThresholdRecord(
            observed_at=day,
            team=manifest.team,
            function_id=fn.function_id,
            metric=fn.sla.metric,
            threshold_op=fn.sla.threshold_op,
            threshold_value=fn.sla.threshold_value,
            source=fn.sla.threshold_source,
        )
        for fn in manifest.functions
    ]
