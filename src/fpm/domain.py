"""Typed domain models. Invariants live in checked types + relationships, not labels."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
ComparisonOperator = Literal[">=", "<=", ">", "<", "=="]
Cadence = Literal["daily", "weekly", "monthly"]
Tier = Literal["irreplaceable", "essential", "important", "nice-to-have"]
Origin = Literal["independent", "asserted", "corroborating"]
# "unscored": a value was measured, but no threshold has been agreed, so nothing is asserted
# about compliance. Distinct from "indeterminate", which means no defensible value at all.
SlaOutcome = Literal["pass", "fail", "indeterminate", "unscored"]
ReviewStatus = Literal["meeting", "at-risk", "breach", "pending_review"]
DetectorSignal = Literal["not_applicable", "insufficient_data", "no_signal", "signal_detected"]
Severity = Literal["low", "medium", "high"]
ApprovalAction = Literal["approve", "revise", "reject", "defer"]

_CADENCE_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MeasurementWindow(_Model):
    start: datetime
    end: datetime


class OsoRunRef(_Model):
    run_id: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    dlt_load_id: str | None = None
    logs_url: str | None = None


class EvidenceRef(_Model):
    raw_payload_hash: Hash | None = None
    canonical_payload_hash: Hash
    request_fingerprint: Hash
    evidence_bundle_hash: Hash
    oso_run_ref: OsoRunRef | None = None


class Claim(_Model):
    value: float | None
    origin: Origin
    source_ref: str
    fetched_at: datetime
    evidence: EvidenceRef | None
    fetched_by: str


class Reading(_Model):
    team: str
    function_id: str
    metric: str
    measurement_window: MeasurementWindow
    claim: Claim
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    adapter: str
    adapter_version: str


class SlaResult(_Model):
    outcome: SlaOutcome
    op: ComparisonOperator | None
    threshold: float | None
    observed: float | None
    measurement_window: MeasurementWindow
    reason: str


class DetectorResult(_Model):
    detector_id: str
    detector_version: str
    signal: DetectorSignal
    evidence_refs: list[str] = Field(default_factory=list)
    note: str = ""


class Flag(_Model):
    flag_id: str
    detector_id: str
    type: str
    severity: Severity
    evidence_refs: list[str] = Field(default_factory=list)
    note: str = ""


class Citation(_Model):
    evidence_bundle_hash: Hash
    source_ref: str


class VersionSet(_Model):
    manifest_commit_sha: str
    commitment_version: str
    measurement_window_start: datetime
    measurement_window_end: datetime
    adapter_version: str
    pipeline_version: str
    rubric_version: str
    detector_versions: dict[str, str]
    model_id: str
    prompt_version: str


class ReviewRecommendation(_Model):
    recommendation_id: str
    team: str
    function_id: str
    review_status: ReviewStatus
    sla_outcome: SlaOutcome
    narrative: str
    citations: list[Citation]
    flags: list[Flag]
    detector_results: list[DetectorResult]
    versions: VersionSet


class ApprovalDecision(_Model):
    action: ApprovalAction
    approver: str
    adjudicated_status: ReviewStatus | None = None
    note: str = ""


class Verdict(_Model):
    recommendation_id: str
    adjudicated_status: ReviewStatus
    approver: str
    approved_at: datetime
    action: ApprovalAction
    note: str = ""


def window_for(cadence: Cadence, as_of: datetime) -> MeasurementWindow:
    return MeasurementWindow(start=as_of - timedelta(days=_CADENCE_DAYS[cadence]), end=as_of)


def make_recommendation_id(
    team: str, function_id: str, window_end: datetime, manifest_commit_sha: str
) -> str:
    return f"{team}:{function_id}:{window_end.date().isoformat()}:{manifest_commit_sha}"
