"""Domain gate. Validates citation-reference admissibility (by evidence hash) and status legality.

Prose-level claim entailment (each sentence tied to a structured claim object) is deferred to a
later plan; this gate does not attempt it.
"""

from __future__ import annotations

from fpm.dossier import ReviewDossier
from fpm.synthesize import SynthesisOutput

_ILLEGAL = {
    "indeterminate": {"meeting", "at-risk", "breach"},
    "pass": {"breach"},
    "fail": {"meeting"},
}


class GateError(ValueError):
    """Raised when a synthesis output violates a domain invariant."""


def admissible_evidence_hashes(dossier: ReviewDossier) -> set[str]:
    c = dossier.reading.claim
    if c.origin == "independent" and c.evidence is not None and c.value is not None:
        return {c.evidence.evidence_bundle_hash}
    return set()


def validate_recommendation(out: SynthesisOutput, dossier: ReviewDossier) -> None:
    if not out.narrative.strip():
        raise GateError("narrative is empty")
    admissible = admissible_evidence_hashes(dossier)
    for h in out.cited_evidence_hashes:
        if h not in admissible:
            raise GateError(f"cited evidence hash {h!r} is not an admissible independent claim")
    if out.review_status in _ILLEGAL.get(dossier.sla_result.outcome, set()):
        raise GateError(
            f"illegal transition: sla_outcome={dossier.sla_result.outcome} "
            f"cannot yield review_status={out.review_status}"
        )
