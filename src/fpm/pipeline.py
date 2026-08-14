"""The review workflow: deterministic pipeline + one bounded inference + gate + human adjudication."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from fpm.adapters.registry import build_adapters
from fpm.bundle import ReviewBundle
from fpm.detectors.corroboration import build_detectors
from fpm.domain import (
    ApprovalDecision,
    Citation,
    ReviewRecommendation,
    VersionSet,
    make_recommendation_id,
)
from fpm.dossier import assemble_dossier
from fpm.gate import admissible_evidence_hashes, validate_recommendation
from fpm.manifest import load_manifest
from fpm.observe import error_reading, measure
from fpm.store import RecordStore, human_adjudicate
from fpm.synthesize import ReviewSynthesizer

PIPELINE_VERSION = "0.1.0"
RUBRIC_VERSION = "0.1.0"


# Kept as an import alias: the reading-construction detail moved to fpm.observe, where the
# scheduled path needs it too, but tests and callers still reach for it here.
_error_reading = error_reading


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
        adapter, reading, sla = measure(fn, manifest.team, adapters, as_of)
        window = reading.measurement_window
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
