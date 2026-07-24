"""The bounded, no-tool INFER call: intent + probed JSON -> a structured SourceSpec proposal."""

from __future__ import annotations

from typing import Literal, Protocol

from fpm.domain import _Model, Cadence
from fpm.manifest import CastOp, DeriveOp, ReduceOp, SourceKind
from fpm.report.probe import Probe


class ExtractProposal(_Model):
    path: str = "$"
    column: str
    cast: CastOp = "float"
    derive: DeriveOp = "value"
    column2: str | None = None
    reduce: ReduceOp = "single"
    timestamp_column: str | None = None


class InferenceOutput(_Model):
    kind: SourceKind
    base_url: str
    endpoint: str
    query: str = ""
    extract: ExtractProposal
    metric: str
    cadence: Cadence | None = None
    rationale: str
    confidence: Literal["low", "medium", "high"]


INFER_JSON_SCHEMA: dict = InferenceOutput.model_json_schema()

_INFER_PROMPT = (
    "You compile a maintainer's plain-English intent plus a probed JSON sample into a declarative "
    "source spec for OSO ingestion. Choose the column that measures the intent, a reduce op that "
    "collapses a series to one value, and a metric name. Do NOT propose a threshold. Return only the "
    "structured result. Intent:\n{intent}\n\nProbe (url, keys, series_hint, sample):\n{probe}"
)


class SourceInferrer(Protocol):
    model_id: str
    prompt_version: str

    def infer(self, intent: str, probe: Probe) -> InferenceOutput: ...


class FakeSourceInferrer:
    """Deterministic stand-in. Used by all unit tests."""

    def __init__(self, model_id: str = "fake", prompt_version: str = "0") -> None:
        self.model_id = model_id
        self.prompt_version = prompt_version

    def infer(self, intent: str, probe: Probe) -> InferenceOutput:
        if probe.series_hint == "list" and "tvl" in probe.top_level_keys:
            return InferenceOutput(
                kind="http-json",
                base_url="https://api.llama.fi",
                endpoint=probe.url,
                extract=ExtractProposal(column="tvl", reduce="latest", timestamp_column="date"),
                metric="chain_tvl_usd",
                cadence="monthly",
                rationale="tvl series reduced to the latest point",
                confidence="high",
            )
        col = probe.top_level_keys[0] if probe.top_level_keys else "value"
        return InferenceOutput(
            kind="http-json",
            base_url=probe.url,
            endpoint=probe.url,
            extract=ExtractProposal(column=col, reduce="single"),
            metric=col,
            rationale="best-effort single-scalar guess",
            confidence="low",
        )


class SdkSourceInferrer:
    """Real bounded inference. No tools. Lazy SDK import. Not exercised by unit tests."""

    def __init__(self, model_id: str, prompt_version: str) -> None:
        self.model_id = model_id
        self.prompt_version = prompt_version

    def infer(self, intent: str, probe: Probe) -> InferenceOutput:
        import anyio
        from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

        prompt = _INFER_PROMPT.format(intent=intent, probe=probe.model_dump_json())
        options = ClaudeAgentOptions(
            model=self.model_id,
            system_prompt="Judgment and language only. Return only the structured result.",
            output_format={"type": "json_schema", "schema": INFER_JSON_SCHEMA},
            # output_format is delivered via the built-in StructuredOutput tool, so it must be
            # permitted. Everything else stays denied: no MCP, and dontAsk rejects any other tool.
            allowed_tools=["StructuredOutput"],
            mcp_servers={},
            strict_mcp_config=True,
            permission_mode="dontAsk",
        )

        async def _run() -> InferenceOutput:
            from fpm.sdk_result import structured_payload

            so: dict | None = None
            text: str | None = None
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, ResultMessage):
                    so = message.structured_output or so
                    text = message.result or text
            return InferenceOutput.model_validate(structured_payload(so, text))

        return anyio.run(_run)
