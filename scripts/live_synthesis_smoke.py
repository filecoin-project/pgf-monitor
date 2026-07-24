"""Quarantined live SDK dry-run. Never imported by unit tests. Persists nothing.

Usage: uv run python scripts/live_synthesis_smoke.py
Requires ANTHROPIC credentials in the environment.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fpm.adapters.registry import build_adapters
from fpm.detectors.base import DETECTORS
from fpm.domain import window_for
from fpm.dossier import assemble_dossier
from fpm.evaluate import evaluate_sla
from fpm.gate import validate_recommendation
from fpm.manifest import load_manifest
from fpm.synthesize import SdkReviewSynthesizer


def main() -> None:
    m = load_manifest("registry/chainsafe.yaml")
    fn = m.functions[0]
    window = window_for(fn.sla.cadence, datetime(2026, 7, 1, tzinfo=timezone.utc))
    reading = build_adapters(Path("fixtures/responses"))["fixture"].fetch(fn, m.team, window)
    sla = evaluate_sla(reading, fn, m.team)
    results = DETECTORS.results(reading, fn)
    dossier = assemble_dossier(m, fn, reading, sla, results, DETECTORS.flags(results))

    out = SdkReviewSynthesizer(model_id="claude-opus-4-8", prompt_version="0").synthesize(dossier)
    validate_recommendation(out, dossier)
    print("review_status:", out.review_status)
    print("citations:", out.cited_evidence_hashes)
    print("narrative:", out.narrative)


if __name__ == "__main__":
    main()
