"""Flatten ReviewBundle verdicts to warehouse rows and land them via a pluggable sink.

The flatten logic + the public/private column split are the durable core; the sink (how rows reach
OSO) is swappable. Plan 6 ships StaticModelSink (push CSV). Production swaps in a scheduled-ingestion
sink without touching these functions.
"""

from __future__ import annotations

import csv
import io
from typing import Protocol

from fpm.bundle import ReviewBundle


def _evidence_hash(bundle: ReviewBundle) -> str:
    ev = bundle.dossier.reading.claim.evidence
    return ev.evidence_bundle_hash if ev is not None else ""


def flatten_public(bundle: ReviewBundle) -> dict:
    """Facts + provenance + the advisory model narrative. No adjudication note, no approver."""
    r, v, d = bundle.recommendation, bundle.verdict, bundle.dossier
    ver = r.versions
    return {
        "recommendation_id": r.recommendation_id,
        "team": r.team,
        "function_id": r.function_id,
        "metric": d.reading.metric,
        "window_start": ver.measurement_window_start.isoformat(),
        "window_end": ver.measurement_window_end.isoformat(),
        "sla_outcome": r.sla_outcome,
        "observed_value": d.sla_result.observed,
        "threshold_op": d.sla_result.op,
        "threshold_value": d.sla_result.threshold,
        "review_status": r.review_status,
        "adjudicated_status": v.adjudicated_status,
        "evidence_bundle_hash": _evidence_hash(bundle),
        "manifest_commit_sha": ver.manifest_commit_sha,
        "adapter_version": ver.adapter_version,
        "pipeline_version": ver.pipeline_version,
        "rubric_version": ver.rubric_version,
        "model_id": ver.model_id,
        "prompt_version": ver.prompt_version,
        "narrative": r.narrative,
        "approved_at": v.approved_at.isoformat(),
    }


def flatten_private(bundle: ReviewBundle) -> dict:
    """The full superset: every public column plus the committee note and approver."""
    row = flatten_public(bundle)
    row["adjudication_note"] = bundle.verdict.note
    row["approver"] = bundle.verdict.approver
    return row


def verdict_rows(bundles: list[ReviewBundle]) -> tuple[list[dict], list[dict]]:
    """Public rows, private rows: deduped by recommendation_id (last wins), sorted by it."""
    pub: dict[str, dict] = {}
    priv: dict[str, dict] = {}
    for b in bundles:
        rid = b.recommendation.recommendation_id
        pub[rid] = flatten_public(b)
        priv[rid] = flatten_private(b)
    order = sorted(pub)
    return [pub[k] for k in order], [priv[k] for k in order]


def to_csv(rows: list[dict]) -> str:
    """Serialize rows to CSV (header + rows). None becomes empty; quoting handles narratives."""
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("" if v is None else v) for k, v in row.items()})
    return buf.getvalue()


class VerdictSink(Protocol):
    def publish(self, name: str, rows: list[dict], public: bool) -> str: ...


class StaticModelClient(Protocol):
    def ensure_static_dataset(self, org_id: str, name: str) -> str: ...
    def ensure_static_model(self, org_id: str, dataset_id: str, name: str) -> str: ...
    def upload_csv(self, static_model_id: str, csv_text: str) -> None: ...
    def run_static_model(self, dataset_id: str) -> None: ...
    def grant_public(self, static_model_id: str) -> None: ...


class FakeStaticModelClient:
    """Deterministic in-memory static-model client for offline tests. No network."""

    def __init__(self) -> None:
        self.datasets: dict[str, str] = {}  # name -> dataset_id
        self.models: dict[str, str] = {}  # model_id -> dataset_id
        self.model_ids: dict[tuple[str, str], str] = {}  # (dataset_id, name) -> model_id
        self.uploaded: dict[str, str] = {}  # model_id -> csv text
        self.granted_public: set[str] = set()
        self.ran: list[str] = []
        self._n = 0

    def _next(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}-{self._n}"

    def ensure_static_dataset(self, org_id: str, name: str) -> str:
        if name not in self.datasets:
            self.datasets[name] = self._next("ds")
        return self.datasets[name]

    def ensure_static_model(self, org_id: str, dataset_id: str, name: str) -> str:
        key = (dataset_id, name)
        if key not in self.model_ids:
            model_id = self._next("sm")
            self.model_ids[key] = model_id
            self.models[model_id] = dataset_id
        return self.model_ids[key]

    def upload_csv(self, static_model_id: str, csv_text: str) -> None:
        self.uploaded[static_model_id] = csv_text

    def run_static_model(self, dataset_id: str) -> None:
        self.ran.append(dataset_id)

    def grant_public(self, static_model_id: str) -> None:
        self.granted_public.add(static_model_id)


class StaticModelSink:
    """Push verdict rows to an OSO Static Model: create -> upload CSV -> run -> (grant public)."""

    def __init__(self, client: StaticModelClient, org_id: str) -> None:
        self._client = client
        self._org_id = org_id

    def publish(self, name: str, rows: list[dict], public: bool) -> str:
        dataset_id = self._client.ensure_static_dataset(self._org_id, name)
        model_id = self._client.ensure_static_model(self._org_id, dataset_id, name)
        self._client.upload_csv(model_id, to_csv(rows))
        self._client.run_static_model(dataset_id)
        if public:
            self._client.grant_public(model_id)
        return model_id


class UnadjudicatedVerdictError(RuntimeError):
    """Raised when a batch carries a verdict no human ever approved."""


#: `fpm review --dev-auto-approve` stamps this approver. It is a development convenience and
#: must never reach a published table — see `assert_adjudicated`.
DEV_AUTO_APPROVER = "dev-auto"


def assert_adjudicated(bundles: list[ReviewBundle]) -> None:
    """Refuse the whole batch if any verdict was auto-approved rather than adjudicated.

    The system's central claim is that a verdict is a human act. `--dev-auto-approve` exists so
    the pipeline can be exercised end-to-end without a reviewer, and `scripts/run_full_review.sh`
    used it while also landing to the normal tables — so the public verdict table could carry
    rows nobody read. Checked before anything is published: a batch is refused whole, never
    half-landed.
    """
    offenders = [
        f"{b.recommendation.team}/{b.recommendation.function_id}"
        for b in bundles
        if b.verdict.approver == DEV_AUTO_APPROVER
    ]
    if offenders:
        raise UnadjudicatedVerdictError(
            f"{len(offenders)} verdict(s) carry approver={DEV_AUTO_APPROVER!r} and were never "
            f"adjudicated by a human: {', '.join(sorted(offenders))}. Re-run `fpm review` without "
            "--dev-auto-approve and adjudicate each call."
        )


def land(
    bundles: list[ReviewBundle],
    sink: VerdictSink,
    # In the filecoin org, `filpgf_public`/`filpgf_private` are PRE-EXISTING UDM datasets
    # (projects/metrics) — these defaults deliberately avoid colliding with them.
    public_name: str = "filpgf_sla_verdicts",
    private_name: str = "filpgf_sla_verdicts_private",
) -> dict:
    """Flatten bundles and publish the public + private tables through the sink."""
    assert_adjudicated(bundles)
    public_rows, private_rows = verdict_rows(bundles)
    return {
        "public": sink.publish(public_name, public_rows, public=True),
        "private": sink.publish(private_name, private_rows, public=False),
    }
