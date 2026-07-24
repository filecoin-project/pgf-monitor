"""Assemble the code-computed dossier that the bounded review inference reads."""

from __future__ import annotations

from fpm.domain import DetectorResult, Flag, Reading, SlaResult, _Model
from fpm.manifest import FunctionSpec, Manifest


class ReviewDossier(_Model):
    team: str
    function_id: str
    sla_statement: str
    sla_result: SlaResult
    reading: Reading
    detector_results: list[DetectorResult]
    flags: list[Flag]
    context: list[dict]


def retrieve_context(team: str, function_id: str) -> list[dict]:
    """Skeleton stub. Structured + semantic retrieval lands in a later plan."""
    return []


def assemble_dossier(
    manifest: Manifest,
    fn: FunctionSpec,
    reading: Reading,
    sla_result: SlaResult,
    detector_results: list[DetectorResult],
    flags: list[Flag],
) -> ReviewDossier:
    return ReviewDossier(
        team=manifest.team,
        function_id=fn.function_id,
        sla_statement=fn.sla.statement,
        sla_result=sla_result,
        reading=reading,
        detector_results=detector_results,
        flags=flags,
        context=retrieve_context(manifest.team, fn.function_id),
    )
