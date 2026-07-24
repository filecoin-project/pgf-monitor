"""Assemble the drafted manifest function (threshold omitted) and validate its source."""

from __future__ import annotations

from datetime import datetime

from fpm.domain import window_for
from fpm.governance.allowlist import host_allowed
from fpm.manifest import ExtractSpec, FunctionSpec, SlaSpec, SourceSpec
from fpm.provision import build_ingestion_config
from fpm.report.infer import InferenceOutput

_TODO = "      # TODO(committee): set threshold {op, value} - required before this passes the validate gate"


def draft_function_yaml(inference: InferenceOutput, intent: str, function_id: str) -> str:
    e = inference.extract
    cadence_line = (
        f"      cadence: {inference.cadence}"
        if inference.cadence
        else "      # TODO cadence: daily|weekly|monthly"
    )
    statement = intent.strip().replace("\n", " ")[:200]
    extract_bits = [
        f"path: {e.path}",
        f"column: {e.column}",
        f"cast: {e.cast}",
        f"reduce: {e.reduce}",
        f"derive: {e.derive}",
    ]
    if e.timestamp_column:
        extract_bits.append(f"timestamp_column: {e.timestamp_column}")
    if e.column2:
        extract_bits.append(f"column2: {e.column2}")
    return (
        "\n".join(
            [
                f"  - function_id: {function_id}",
                "    tier: important  # TODO: confirm kernel tier",
                "    sla:",
                f'      statement: "{statement}"',
                f"      metric: {inference.metric}",
                _TODO,
                cadence_line,
                "    source:",
                "      adapter: oso",
                f"      kind: {inference.kind}",
                f'      base_url: "{inference.base_url}"',
                f'      endpoint: "{inference.endpoint}"',
                f'      query: "{inference.query}"',
                "      extract: { " + ", ".join(extract_bits) + " }",
            ]
        )
        + "\n"
    )


def validate_source(
    inference: InferenceOutput, team: str, allowlist: set[str], as_of: datetime
) -> list[str]:
    warnings: list[str] = []
    if not host_allowed(inference.base_url, allowlist):
        warnings.append(f"base_url host is not on the committee allowlist: {inference.base_url}")
    fn = FunctionSpec(
        function_id="_draft",
        tier="important",
        sla=SlaSpec(
            statement="draft",
            metric=inference.metric,
            threshold_op=">=",
            threshold_value=0.0,
            cadence=inference.cadence or "monthly",
        ),
        source=SourceSpec(
            adapter="oso",
            kind=inference.kind,
            base_url=inference.base_url,
            endpoint=inference.endpoint,
            query=inference.query,
            extract=ExtractSpec(
                path=inference.extract.path,
                column=inference.extract.column,
                cast=inference.extract.cast,
                reduce=inference.extract.reduce,
                timestamp_column=inference.extract.timestamp_column,
                derive=inference.extract.derive,
                column2=inference.extract.column2,
            ),
        ),
    )
    try:
        build_ingestion_config(fn, window_for(fn.sla.cadence, as_of), team)
    except Exception as exc:  # translation must succeed
        warnings.append(f"source does not translate to an OSO ingestion config: {exc}")
    return warnings
