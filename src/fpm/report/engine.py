"""The report workflow: probe -> infer -> apply -> draft, aggregated into a ReportDraft."""

from __future__ import annotations

from datetime import datetime

from fpm.domain import _Model
from fpm.report.apply import observed_value
from fpm.report.draft import draft_function_yaml, validate_source
from fpm.report.infer import SourceInferrer
from fpm.report.probe import Fetch, _http_fetch, probe


class ReportDraft(_Model):
    manifest_yaml: str
    observed_value: float | None
    metric: str
    confidence: str
    warnings: list[str]


def run_report(
    intent: str,
    url: str,
    team: str,
    function_id: str,
    inferrer: SourceInferrer,
    allowlist: set[str],
    as_of: datetime,
    fetch: Fetch = _http_fetch,
) -> ReportDraft:
    p = probe(url, fetch)
    inference = inferrer.infer(intent, p)
    observed = observed_value(inference, p)
    yaml_block = draft_function_yaml(inference, intent, function_id)
    warnings = validate_source(inference, team, allowlist, as_of)
    if inference.confidence == "low":
        warnings.append("low confidence: review the inferred field/reduce carefully")
    if observed is None:
        warnings.append(
            "observed value is None: the extract did not resolve a value from the sample"
        )
    return ReportDraft(
        manifest_yaml=yaml_block,
        observed_value=observed,
        metric=inference.metric,
        confidence=inference.confidence,
        warnings=warnings,
    )
