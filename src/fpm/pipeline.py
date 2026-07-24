"""The review workflow: deterministic pipeline + one bounded inference + gate + human adjudication."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from fpm.adapters.registry import UnsupportedAdapterError, build_adapters
from fpm.bundle import ReviewBundle
from fpm.detectors.corroboration import build_detectors
from fpm.domain import (
    ApprovalDecision,
    Citation,
    Claim,
    MeasurementWindow,
    Reading,
    ReviewRecommendation,
    VersionSet,
    make_recommendation_id,
    window_for,
)
from fpm.dossier import assemble_dossier
from fpm.evaluate import evaluate_sla
from fpm.gate import admissible_evidence_hashes, validate_recommendation
from fpm.manifest import FunctionSpec, load_manifest
from fpm.store import RecordStore, human_adjudicate
from fpm.synthesize import ReviewSynthesizer

PIPELINE_VERSION = "0.1.0"
RUBRIC_VERSION = "0.1.0"


def _error_reading(
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


def run_review(
    manifest_path: str | Path,
    fixtures_dir: Path,
    synthesizer: ReviewSynthesizer,
    store: RecordStore,
    decide: Callable[[ReviewRecommendation], ApprovalDecision],
    as_of: datetime,
    manifest_commit_sha: str = "uncommitted",
    oso_client=None,
    org_id: str = "",
    allowlist: set[str] | None = None,
    poll_sleep: float = 0.0,
) -> list[ReviewBundle]:
    manifest = load_manifest(manifest_path)
    adapters = build_adapters(
        fixtures_dir,
        oso_client=oso_client,
        org_id=org_id,
        allowlist=allowlist,
        poll_sleep=poll_sleep,
    )
    detectors = build_detectors(oso_client)
    persisted: list[ReviewBundle] = []

    for fn in manifest.functions:
        adapter = adapters[fn.source.adapter]
        if adapter.name != fn.source.adapter:  # defensive: registry contract
            raise UnsupportedAdapterError(fn.source.adapter)
        window = window_for(fn.sla.cadence, as_of)
        try:
            reading = adapter.fetch(fn, manifest.team, window)
        except Exception as exc:
            # Isolate a single function's fetch failure (egress block, network, API error) so it
            # does not abort the whole review. The value-less reading yields an indeterminate
            # verdict with the error recorded, and the remaining functions still run.
            reading = _error_reading(fn, manifest.team, window, exc)
        sla = evaluate_sla(reading, fn, manifest.team)
        results = detectors.results(reading, fn)
        flags = detectors.flags(results)
        dossier = assemble_dossier(manifest, fn, reading, sla, results, flags)

        out = synthesizer.synthesize(dossier)
        validate_recommendation(out, dossier)

        admissible = admissible_evidence_hashes(dossier)
        citations = [
            Citation(evidence_bundle_hash=h, source_ref=reading.claim.source_ref)
            for h in out.cited_evidence_hashes
            if h in admissible
        ]
        rec = ReviewRecommendation(
            recommendation_id=make_recommendation_id(
                manifest.team, fn.function_id, window.end, manifest_commit_sha
            ),
            team=manifest.team,
            function_id=fn.function_id,
            review_status=out.review_status,
            sla_outcome=sla.outcome,
            narrative=out.narrative,
            citations=citations,
            flags=flags,
            detector_results=results,
            versions=VersionSet(
                manifest_commit_sha=manifest_commit_sha,
                commitment_version="1",
                measurement_window_start=window.start,
                measurement_window_end=window.end,
                adapter_version=adapter.version,
                pipeline_version=PIPELINE_VERSION,
                rubric_version=RUBRIC_VERSION,
                detector_versions=detectors.versions(),
                model_id=synthesizer.model_id,
                prompt_version=synthesizer.prompt_version,
            ),
        )
        bundle = human_adjudicate(rec, dossier, out, decide)
        if bundle is not None:
            store.save_adjudication(bundle)
            persisted.append(bundle)

    return persisted
