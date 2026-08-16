"""Bounded review inference behind one interface. Tests use the fake; the SDK impl is live-only."""

from __future__ import annotations

from typing import Protocol

from pydantic import Field

from fpm.domain import ReviewStatus, _Model
from fpm.dossier import ReviewDossier

_STATUS_FROM_SLA: dict[str, ReviewStatus] = {
    "pass": "meeting",
    "fail": "breach",
    "indeterminate": "pending_review",
    "unscored": "pending_review",
}


class SynthesisOutput(_Model):
    review_status: ReviewStatus
    narrative: str
    cited_evidence_hashes: list[str]
    flag_notes: dict[str, str] = Field(default_factory=dict)


SYNTHESIS_JSON_SCHEMA: dict = SynthesisOutput.model_json_schema()


class ReviewSynthesizer(Protocol):
    model_id: str
    prompt_version: str

    def synthesize(self, dossier: ReviewDossier) -> SynthesisOutput: ...


class FakeReviewSynthesizer:
    """Deterministic stand-in for the model. Used by all unit tests."""

    def __init__(self, model_id: str = "fake", prompt_version: str = "0") -> None:
        self.model_id = model_id
        self.prompt_version = prompt_version

    def synthesize(self, dossier: ReviewDossier) -> SynthesisOutput:
        claim = dossier.reading.claim
        admissible = (
            claim.origin == "independent" and claim.evidence is not None and claim.value is not None
        )
        cites = [claim.evidence.evidence_bundle_hash] if admissible else []
        narrative = (
            f"{dossier.team}/{dossier.function_id}: SLA outcome {dossier.sla_result.outcome} "
            f"({dossier.sla_result.reason}); {len(dossier.flags)} flag(s)."
        )
        return SynthesisOutput(
            review_status=_STATUS_FROM_SLA[dossier.sla_result.outcome],
            narrative=narrative,
            cited_evidence_hashes=cites,
        )


class SdkReviewSynthesizer:
    """Real bounded inference. No tools. Lazily imports the SDK. Not exercised by unit tests."""

    def __init__(self, model_id: str, prompt_version: str) -> None:
        self.model_id = model_id
        self.prompt_version = prompt_version

    def synthesize(self, dossier: ReviewDossier) -> SynthesisOutput:
        import anyio
        from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

        prompt = (
            "You are a ProPGF review synthesizer. Given a code-computed dossier as JSON, do not "
            "recompute the SLA. Propose a review_status, write a factual narrative, and cite only "
            "evidence_bundle_hash values that appear on independent claims in the dossier. "
            "Dossier:\n" + dossier.model_dump_json()
        )
        options = ClaudeAgentOptions(
            model=self.model_id,
            system_prompt="Return only the structured result. Judgment and language only.",
            output_format={"type": "json_schema", "schema": SYNTHESIS_JSON_SCHEMA},
            # output_format is delivered via the built-in StructuredOutput tool, so it must be
            # permitted. Everything else stays denied: no MCP, and dontAsk rejects any other tool.
            allowed_tools=["StructuredOutput"],
            mcp_servers={},
            strict_mcp_config=True,
            permission_mode="dontAsk",
        )

        async def _run() -> SynthesisOutput:
            from fpm.sdk_result import structured_payload

            so: dict | None = None
            text: str | None = None
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, ResultMessage):
                    so = message.structured_output or so
                    text = message.result or text
            return SynthesisOutput.model_validate(structured_payload(so, text))

        return anyio.run(_run)
