"""The deterministic half of the pipeline: fetch a source, evaluate the SLA, stop.

`run_review` adds inference and human adjudication on top of this; a scheduled observation run
must not, because there is nobody at the keyboard to adjudicate and a nightly LLM narrative would
be a nondeterministic artifact nobody asked for. Both paths call `measure`, so the number a
reviewer adjudicates and the number the time series records can never drift apart.

An Observation is one row of `data/observations.csv` — see fpm.observations for the store.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from fpm.guards import age_growth_violation, capture_refused_reading
from fpm.manifest import FunctionSpec, Manifest, load_manifest


# The note on a reading the run never got to. A substring match is what tests and the CLI both
# key on, so it stays a constant rather than a literal repeated at three call sites.
TRUNCATED_NOTE = "not attempted: run truncated at its deadline"


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
    for key in ("fetch_error", "transform_error", "sql_error"):
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


def apply_age_guard(
    fn: FunctionSpec,
    obs: Observation,
    previous: dict[tuple[str, str, str], tuple[str, float]],
    reading: Reading | None = None,
    capture_dir: str | Path | None = None,
) -> None:
    """Null an age reading that grew faster than wall time. Mutates `obs` in place.

    Applies only to `derive: age_*` metrics, because the invariant only holds for them: a release
    count or a pool balance may jump by any amount overnight and be perfectly true. See
    `fpm.guards` for why a null beats publishing the number.

    When `reading` is supplied, the rows and the OSO run reference behind the refused value are
    written to a capture file first. The refusal is the only moment that evidence exists -- the
    ingestion table is overwritten on the next run -- so it is preserved before it is discarded.
    """
    extract = fn.source.extract
    if obs.observed_value is None or extract is None:
        return
    if not str(extract.derive).startswith("age_"):
        return
    prior = previous.get((obs.team, obs.function_id, obs.metric))
    if prior is None:
        return
    prev_day, prev_value = prior
    unit_seconds = 1.0 if str(extract.derive) == "age_seconds" else 86400.0
    reason = age_growth_violation(
        prev_value, prev_day, obs.observed_value, obs.observed_at, unit_seconds
    )
    if reason is None:
        return
    if reading is not None:
        capture_refused_reading(
            team=obs.team,
            function_id=obs.function_id,
            metric=obs.metric,
            observed_at=obs.observed_at,
            refused_value=obs.observed_value,
            previous_day=prev_day,
            previous_value=prev_value,
            reason=reason,
            reading=reading,
            directory=capture_dir,
            # The URL OSO was asked to fetch. Recorded so a control fetch can ask GitHub the
            # SAME question directly, seconds later, from a different network path -- which is
            # what separates "GitHub served a stale page" from "something on OSO's path did".
            endpoint=fn.source.endpoint or fn.source.base_url,
        )
    obs.observed_value = None
    obs.note = reason
    obs.outcome = "indeterminate"


def unattempted(fn: FunctionSpec, team: str, as_of: datetime, method: str) -> Observation:
    """The row for a function this run never got to.

    Deliberately shaped like any other value-less reading so nothing downstream needs to learn a
    new state, but with a note that distinguishes it from a source that went dark. Omitting the
    row entirely was the other option and it is the wrong one: `thresholds_for` already argues
    that an absence must be recorded rather than inferred, and after the 2026-09-18 truncation a
    silent skip would have been indistinguishable from a night the monitor did not run.
    """
    return Observation(
        observed_at=as_of.date().isoformat(),
        team=team,
        function_id=fn.function_id,
        metric=fn.sla.metric,
        observed_value=None,
        method=method,
        note=TRUNCATED_NOTE,
        outcome="indeterminate",
    )


def retryable(reading: Reading) -> bool:
    """True when the FETCH failed, as opposed to a source that answered without a value.

    An OSO ingestion run that ended FAILED or CANCELED, or a fetch that raised. These are the
    platform's failures, and they are worth asking again: on 2026-10-09 three of 46 runs failed
    within the same five seconds on an OPA 502 inside OSO's Trino, and every one succeeded when
    re-run. A run still going at the poll ceiling is NOT retried -- a second run would race the
    first. Nor is a warehouse read that returned the wrong shape, or a source that answered
    with no value: asking again gets the same answer.
    """
    meta = reading.source_metadata
    return "fetch_error" in meta or meta.get("run_status") in ("FAILED", "CANCELED")


def observe_function(
    fn: FunctionSpec,
    team: str,
    adapters: dict[str, Adapter],
    as_of: datetime,
    method: str,
    previous: dict[tuple[str, str, str], tuple[str, float]] | None = None,
    capture_dir: str | Path | None = None,
) -> tuple[Observation, bool]:
    """Measure one function and turn it into its row, age guard included.

    Also says whether the fetch failed in a way worth retrying (see `retryable`).
    """
    _, reading, sla = measure(fn, team, adapters, as_of)
    obs = to_observation(fn, team, reading, sla, as_of, method)
    apply_age_guard(fn, obs, previous or {}, reading=reading, capture_dir=capture_dir)
    return obs, retryable(reading)


def observe_all(
    manifest_paths: list[str | Path],
    fixtures_dir: Path,
    as_of: datetime,
    method: str = "nightly",
    oso_client=None,
    org_id: str = "",
    allowlist: set[str] | None = None,
    poll_sleep: float = 0.0,
    sql_allowlist: set[str] | None = None,
    previous: dict[tuple[str, str, str], tuple[str, float]] | None = None,
    capture_dir: str | Path | None = None,
    should_continue: Callable[[], bool] | None = None,
    workers: int = 1,
    retries: int = 0,
    on_observation: Callable[[Observation, float], None] | None = None,
    on_retry: Callable[[Observation, float, int], None] | None = None,
    on_manifest: Callable[[Path, list[Observation]], None] | None = None,
) -> tuple[list[Observation], list[tuple[Path, Exception]]]:
    """Measure every function in every manifest, up to `workers` of them at once.

    Returns (observations, failed). Observations come back in manifest order and, within a
    manifest, in function order, whatever order they finished in -- so two nights' outputs stay
    comparable line for line. `failed` holds each manifest that could not be measured (it would
    not load, or a function raised past `measure`'s own isolation) with the error; its functions
    produce no rows, and the other manifests are unaffected.

    Why concurrent: each live function is a whole OSO ingestion job (~20s on the platform, plus
    polling and two Trino reads), and nearly all of that is waiting. Run one at a time, 46 of
    them took 28-37 minutes against a 40-minute deadline and on 2026-10-07 a slow platform night
    pushed past it.

    The functions are queued in manifest order, and the pool takes them first in, first out, so
    `order_by_cost` still decides what a short night collects first.

    RETRIES. A function whose fetch failed (see `retryable`) is queued, not retried on the
    spot, and the queue runs after every function has had its first attempt: a retry never
    displaces a commitment that has not been asked at all, and by then a transient platform
    fault has had minutes to clear. Up to `retries` rounds; whatever the last attempt says is
    the row. Retrying is also what keeps a failure from leaking into TOMORROW: a run that fails
    at dlt's load step leaves its fetched package pending, and the next run of that dataset
    loads THAT package and ignores its own fetch. Seen live 2026-10-09, and almost certainly
    why 2026-10-08 recorded 2026-10-07's data for the two load failures that night. A retry
    tonight drains the package while it is minutes old instead of a day old.

    `should_continue` is checked as each attempt STARTS, and once it goes false it stays false:
    every function not yet started gets an `unattempted` row, while the ones already in flight
    finish and keep their values. A retry the deadline stops keeps its failed attempt as the
    row -- the function WAS attempted, and the failure is the truer note. Same promise as
    `observe`, one row per function, always.

    All callbacks run on the CALLING thread, never on a worker, so a caller can print and write
    files without locking. `on_observation(obs, seconds)` fires as each function's FINAL
    attempt lands (not for an unattempted one; see `observe`). `on_retry(obs, seconds, attempt)`
    fires for an attempt that failed and was queued again, `attempt` counting from 1.
    `on_manifest(path, observations)` fires once per manifest, as soon as its last function is
    final, so the caller can persist it immediately: a killed process then loses only the
    manifests still in flight.
    """
    adapters = build_adapters(
        fixtures_dir,
        oso_client=oso_client,
        org_id=org_id,
        allowlist=allowlist,
        poll_sleep=poll_sleep,
        sql_allowlist=sql_allowlist,
    )
    failed: list[tuple[Path, Exception]] = []
    manifests: list[tuple[Path, Manifest]] = []
    for path in map(Path, manifest_paths):
        try:
            manifests.append((path, load_manifest(path)))
        except Exception as exc:
            failed.append((path, exc))

    lock = threading.Lock()
    stopped = [False]

    def run(fn: FunctionSpec, team: str) -> tuple[Observation, float, bool] | None:
        """One attempt, or None when the deadline has passed and it was not started."""
        with lock:
            if not stopped[0] and should_continue is not None and not should_continue():
                stopped[0] = True
            if stopped[0]:
                return None
        started = time.monotonic()
        obs, again = observe_function(fn, team, adapters, as_of, method, previous, capture_dir)
        return obs, time.monotonic() - started, again

    results: dict[Path, dict[int, Observation]] = {path: {} for path, _ in manifests}
    remaining = {path: len(manifest.functions) for path, manifest in manifests}
    broken: set[Path] = set()

    def final(path: Path, manifest: Manifest, index: int, obs: Observation) -> None:
        results[path][index] = obs
        remaining[path] -= 1
        if remaining[path] == 0 and on_manifest is not None:
            on_manifest(path, [results[path][i] for i in range(len(manifest.functions))])

    queue = [
        (path, manifest, index, fn)
        for path, manifest in manifests
        for index, fn in enumerate(manifest.functions)
    ]
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for attempt in range(1, retries + 2):
            futures = {pool.submit(run, item[3], item[1].team): item for item in queue}
            queue = []
            for future in as_completed(futures):
                path, manifest, index, fn = item = futures[future]
                if path in broken:
                    continue
                try:
                    got = future.result()
                except Exception as exc:
                    broken.add(path)
                    failed.append((path, exc))
                    continue
                if got is None:
                    # Not started. A first attempt becomes an `unattempted` row, with no progress
                    # callback: the log line reports what a metric DID, and nothing was done --
                    # reporting it would make a truncated night look like a night of broken
                    # sources. A retry keeps the failed attempt it already has.
                    if attempt == 1:
                        final(path, manifest, index, unattempted(fn, manifest.team, as_of, method))
                    else:
                        final(path, manifest, index, results[path].pop(index))
                    continue
                obs, seconds, again = got
                if again and attempt <= retries:
                    results[path][index] = obs
                    queue.append(item)
                    if on_retry is not None:
                        on_retry(obs, seconds, attempt)
                    continue
                if on_observation is not None:
                    on_observation(obs, seconds)
                final(path, manifest, index, obs)
            if not queue:
                break

    out = [
        results[path][i]
        for path, manifest in manifests
        if path not in broken
        for i in range(len(manifest.functions))
    ]
    return out, failed


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
    sql_allowlist: set[str] | None = None,
    previous: dict[tuple[str, str, str], tuple[str, float]] | None = None,
    capture_dir: str | Path | None = None,
    should_continue: Callable[[], bool] | None = None,
) -> list[Observation]:
    """Measure every function in one manifest, one at a time. One Observation per function, always.

    `on_observation` fires as each metric lands, so a caller can report progress during a run
    that takes tens of minutes rather than only at the end.

    `previous` maps (team, function_id, metric) -> (day, value) for the last recorded reading, and
    is what lets the age guard compare today against yesterday. Injected rather than read here so
    this stays testable without a CSV; the CLI supplies it from the series. Omitted means no guard,
    which is the right default for a first run with no history to check against.

    `should_continue` is checked BEFORE each function and stops the run when it goes false. It is
    a predicate rather than a deadline so this stays testable with no clock; the CLI supplies one
    closed over the wall-clock budget. The check is per function, not per manifest, because one
    manifest can be five metrics at the 320s poll ceiling -- 27 minutes, enough to overshoot any
    budget a per-manifest check could honour. Functions after the stop get `unattempted` rows, so
    the one-per-function promise above holds on a truncated run too.

    The single-manifest, single-worker case of `observe_all`, and raises where that would report
    the manifest as failed.
    """
    out, failed = observe_all(
        [manifest_path],
        fixtures_dir,
        as_of,
        method=method,
        oso_client=oso_client,
        org_id=org_id,
        allowlist=allowlist,
        poll_sleep=poll_sleep,
        sql_allowlist=sql_allowlist,
        previous=previous,
        capture_dir=capture_dir,
        should_continue=should_continue,
        on_observation=None if on_observation is None else (lambda obs, _s: on_observation(obs)),
    )
    if failed:
        raise failed[0][1]
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
