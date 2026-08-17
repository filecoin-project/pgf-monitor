"""OsoAdapter: fetch a Reading by driving an OSO ingestion. Async run, bounded poll, then read back.

The Adapter interface stays synchronous (fetch blocks on the run poll). A non-terminal run within
poll_attempts, or a FAILED/CANCELED run, yields a value-less Reading so the evaluator returns
indeterminate. No sleep is used: the FakeOsoClient is deterministic and the live client's own
network latency paces the loop.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timezone

from fpm.domain import Claim, EvidenceRef, MeasurementWindow, OsoRunRef, Reading
from fpm.hashing import oso_evidence
from fpm.manifest import FunctionSpec
from fpm.oso.client import OsoIngestionClient, RunInfo
from fpm.provision import (
    MissingSecretError,
    assert_egress_allowed,
    build_ingestion_config,
    config_fingerprint,
    config_shape_fingerprint,
    dataset_name,
    missing_secret,
)
from fpm.reduce import derive_observed
from fpm.transform.validate import bind_transform_sql, validate_transform_sql

_TERMINAL = {"SUCCESS", "FAILED", "CANCELED"}


class OsoAdapter:
    name = "oso"
    version = "0.1.0"

    def __init__(
        self,
        client: OsoIngestionClient,
        org_id: str,
        allowlist: set[str],
        poll_attempts: int = 30,
        poll_sleep: float = 0.0,
        dataset_namer: Callable[[str, str], str] = dataset_name,
    ) -> None:
        self._client = client
        self._org_id = org_id
        self._allowlist = allowlist
        self._poll_attempts = poll_attempts
        self._poll_sleep = poll_sleep
        # The durable name by default. The PR dry-run overrides it so a throwaway measurement
        # provisions its own dataset and can never reuse — or delete — a production one.
        self._dataset_namer = dataset_namer

    def _ensure_dataset(self, fn: FunctionSpec, team: str, window: MeasurementWindow) -> str:
        name = self._dataset_namer(team, fn.function_id)
        desired = build_ingestion_config(fn, window, team)
        dataset_id = self._client.find_dataset(self._org_id, name)
        if dataset_id is not None:
            # A changed source declaration must propagate. OSO has no config-update mutation, so
            # if the attached config no longer matches, delete the stale dataset and recreate it.
            # (A config change is itself a goalpost event; fresh lineage is appropriate.)
            current = self._client.get_config(dataset_id)
            if current is None or config_shape_fingerprint(current) != config_shape_fingerprint(
                desired
            ):
                self._client.delete_dataset(dataset_id)
                dataset_id = None
        if dataset_id is None:
            # The one moment the plaintext credential is required. Refuse rather than attach a
            # value-less auth block, which OSO would accept and then fetch anonymously — turning a
            # missing secret into a silently rate-limited metric instead of a visible error.
            ref = missing_secret(fn)
            if ref is not None:
                raise MissingSecretError(
                    f"{fn.function_id} needs ${ref} to provision its source. Runs against an "
                    f"EXISTING dataset do not need it (OSO keeps the credential), so this means "
                    f"the dataset must be created or its config changed. Provision from a host "
                    f"that has ${ref}, or run `fpm observe --reprovision` there."
                )
            assert_egress_allowed(fn, self._allowlist)
            dataset_id = self._client.create_dataset(self._org_id, name, name)
            self._client.attach_rest_config(dataset_id, desired)
        return dataset_id

    def _poll(self, dataset_id: str, run_id: str) -> RunInfo | None:
        run: RunInfo | None = None
        for attempt in range(self._poll_attempts):
            # Polling spans minutes of live API calls; a transient error (5xx, network blip)
            # must not abort the run. Absorb it and keep polling until terminal or timeout.
            try:
                runs = {r.run_id: r for r in self._client.get_runs(dataset_id)}
                run = runs.get(run_id)
                if run and run.status in _TERMINAL:
                    return run
            except Exception:
                pass  # transient; retry on the next attempt
            if self._poll_sleep and attempt < self._poll_attempts - 1:
                time.sleep(self._poll_sleep)
        return run if run and run.run_id == run_id else None

    def _reading(
        self,
        fn: FunctionSpec,
        team: str,
        window: MeasurementWindow,
        value: float | None,
        run: RunInfo | None,
        rows: list[dict],
        fingerprint: dict,
        fetched_at: datetime,
        transform_error: str | None = None,
    ) -> Reading:
        run_ref = OsoRunRef(
            run_id=run.run_id if run else "none",
            status=run.status if run else "TIMEOUT",
            started_at=run.started_at if run else None,
            finished_at=run.finished_at if run else None,
            dlt_load_id=run.dlt_load_id if run else None,
            logs_url=run.logs_url if run else None,
        )
        canon, rf, bundle = oso_evidence(rows, fingerprint, run_ref.model_dump(mode="json"))
        claim = Claim(
            value=value,
            origin="independent",
            source_ref=fn.source.base_url,
            fetched_at=fetched_at,
            evidence=EvidenceRef(
                raw_payload_hash=None,
                canonical_payload_hash=canon,
                request_fingerprint=rf,
                evidence_bundle_hash=bundle,
                oso_run_ref=run_ref,
            ),
            fetched_by=f"{self.name}@{self.version}",
        )
        source_metadata = {"kind": fn.source.kind, "run_status": run_ref.status}
        if transform_error is not None:
            source_metadata["transform_error"] = transform_error
        return Reading(
            team=team,
            function_id=fn.function_id,
            metric=fn.sla.metric,
            measurement_window=window,
            claim=claim,
            source_metadata=source_metadata,
            adapter=self.name,
            adapter_version=self.version,
        )

    def _transform_value(
        self, fn: FunctionSpec, full: str, window: MeasurementWindow, now: datetime
    ) -> tuple[float | None, str | None]:
        """Run the bound transform SQL read-only. Return (value, None) on success, or
        (None, reason) if the transform is unusable, so the caller can surface why."""
        try:
            tree = validate_transform_sql(fn.transform.sql)
            bound = bind_transform_sql(tree, full, window.start, window.end, now)
            result = self._client.query(bound)
        except Exception as exc:
            # A validation failure (TransformSqlError) or a query error both map to a value-less
            # reading -> indeterminate, matching the poll-resilience ethos (a bad function never
            # aborts the batch). TransformSqlError is an Exception subclass, so this catches it.
            return None, f"transform failed: {exc}"
        if len(result) != 1:
            return None, f"transform returned {len(result)} rows, expected 1"
        cells = list(result[0].values())
        if len(cells) != 1 or cells[0] is None:
            return None, "transform result is not a single non-null cell"
        try:
            return float(cells[0]), None
        except (TypeError, ValueError):
            return None, "transform result is not numeric"

    def _read_rows(self, full: str | None) -> list[dict]:
        """Read the raw table, treating a not-yet-queryable table as empty (retryable)."""
        if not full:
            return []
        try:
            return self._client.query(f"SELECT * FROM {full}")
        except Exception:
            return []

    def fetch(self, fn: FunctionSpec, team: str, window: MeasurementWindow) -> Reading:
        fetched_at = datetime.now(timezone.utc)
        fingerprint = config_fingerprint(fn, window)
        dataset_id = self._ensure_dataset(fn, team, window)
        run_id = self._client.trigger_run(dataset_id)
        run = self._poll(dataset_id, run_id)
        if run is None or run.status != "SUCCESS":
            return self._reading(fn, team, window, None, run, [], fingerprint, fetched_at)
        full = self._client.table_full_name(dataset_id)
        rows = self._read_rows(full)
        # A freshly-materialized table can lag the run's SUCCESS by seconds-to-minutes
        # (Iceberg metadata propagation) — an immediate read then sees 0 rows and the
        # function goes indeterminate for no real reason. Retry bounded by poll_sleep.
        for _ in range(6):
            if rows or not self._poll_sleep:
                break
            time.sleep(self._poll_sleep)
            if not full:
                full = self._client.table_full_name(dataset_id)
            rows = self._read_rows(full)
        if fn.transform is not None:
            if full:
                value, transform_error = self._transform_value(fn, full, window, fetched_at)
            else:
                value, transform_error = None, "no raw table available"
        elif fn.source.extract:
            value = derive_observed(rows, fn.source.extract, fetched_at)
            transform_error = None
        else:
            value = None
            transform_error = None
        return self._reading(
            fn, team, window, value, run, rows, fingerprint, fetched_at, transform_error
        )
