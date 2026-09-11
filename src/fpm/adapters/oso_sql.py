"""OsoSqlAdapter: read a metric straight out of the OSO warehouse with committee-allowlisted SQL.

Where OsoAdapter provisions a dlt ingestion, triggers a run, polls it to terminal and reads the
raw table it lands, this adapter runs ONE SELECT against tables already in the warehouse. There is
no dataset, no run and no egress, so the provisioning failure modes simply do not exist here — no
missing secret, no wedged dlt pending package, no rate limit, no host allowlist.

Use it when OSO already holds the data and the number needs a join the http-json path cannot
express. A transform binds exactly one `raw` table, so a metric that must combine two tables
(Filecoin Pay volume per operator joined to the rails table that names the service) has no shape
in that regime at all.

THE SAFETY STORY IS DIFFERENT, and it is why this kind is narrow. The provisioning host's
OSO_API_KEY is org-scoped: it can read `filpgf_private.*` and
`funding_model_static.applicant_identity`. Unrestricted warehouse SQL in a community PR could
therefore lift applicant identity into a PUBLIC observation value — the same objection that ruled
out the Python-UDM escape hatch. `validate_warehouse_sql` blocks it structurally, the way the
`raw` binding does for a transform: one SELECT, one scalar, and every table reference fully
qualified AND on `registry/_sql_allowlist.txt`, which is read from the BASE ref, never the head.

A failure — rejected SQL, a query error, a result that is not one non-null numeric cell — yields a
value-less Reading, so the SLA evaluates to indeterminate with the reason recorded and the rest of
the batch still runs. Same ethos as a FAILED ingestion run.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fpm.domain import Claim, EvidenceRef, MeasurementWindow, Reading
from fpm.hashing import oso_evidence
from fpm.manifest import FunctionSpec
from fpm.oso.client import OsoIngestionClient
from fpm.transform.validate import bind_warehouse_sql, validate_warehouse_sql


class OsoSqlAdapter:
    name = "oso-sql"
    version = "0.1.0"

    def __init__(self, client: OsoIngestionClient, allowed_tables: set[str] | None = None) -> None:
        self._client = client
        # Defaults to EMPTY, not permissive: an adapter built without the committee list must
        # reject every table rather than accept every table.
        self._allowed = allowed_tables or set()

    def _fingerprint(self, fn: FunctionSpec, window: MeasurementWindow) -> dict:
        """The reproducibility anchor: the DECLARED sql plus the window.

        Never the bound SQL — its timestamp literals move every run, so a fingerprint over it
        would differ daily and be useless for telling a changed commitment from a new reading.
        """
        return {
            "kind": fn.source.kind,
            "sql": fn.source.sql,
            "window_start": window.start.isoformat(),
            "window_end": window.end.isoformat(),
        }

    def _value(
        self, fn: FunctionSpec, window: MeasurementWindow, now: datetime
    ) -> tuple[float | None, str | None, list[dict]]:
        """Run the bound SQL read-only. (value, None, rows) on success, (None, reason, rows) if not."""
        try:
            tree = validate_warehouse_sql(fn.source.sql, self._allowed)
            bound = bind_warehouse_sql(tree, window.start, window.end, now)
            rows = self._client.query(bound)
        except Exception as exc:
            # TransformSqlError (a ValueError) and any query error both land here and map to a
            # value-less reading, so one bad function never aborts the batch.
            return None, f"sql failed: {exc}", []
        if len(rows) != 1:
            return None, f"sql returned {len(rows)} rows, expected 1", rows
        cells = list(rows[0].values())
        if len(cells) != 1 or cells[0] is None:
            return None, "sql result is not a single non-null cell", rows
        try:
            return float(cells[0]), None, rows
        except (TypeError, ValueError):
            return None, "sql result is not numeric", rows

    def fetch(self, fn: FunctionSpec, team: str, window: MeasurementWindow) -> Reading:
        fetched_at = datetime.now(timezone.utc)
        value, error, rows = self._value(fn, window, fetched_at)
        canon, rf, bundle = oso_evidence(rows, self._fingerprint(fn, window), {})
        claim = Claim(
            value=value,
            origin="independent",
            # No endpoint was called. Name the warehouse rather than leaving provenance blank,
            # so a citation on this reading still says where the number came from.
            source_ref=fn.source.base_url or "oso-warehouse",
            fetched_at=fetched_at,
            evidence=EvidenceRef(
                raw_payload_hash=None,
                canonical_payload_hash=canon,
                request_fingerprint=rf,
                # There is no ingestion run to reference, and inventing a placeholder one would
                # make a SQL read look like a provisioned fetch in the evidence bundle.
                oso_run_ref=None,
                evidence_bundle_hash=bundle,
            ),
            fetched_by=f"{self.name}@{self.version}",
        )
        source_metadata = {"kind": fn.source.kind}
        if error is not None:
            source_metadata["sql_error"] = error
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
