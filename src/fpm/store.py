"""Local persistence + typed human adjudication. One atomic ReviewBundle per adjudication."""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from fpm.bundle import ReviewBundle
from fpm.domain import ApprovalDecision, ReviewRecommendation, Verdict
from fpm.dossier import ReviewDossier
from fpm.synthesize import SynthesisOutput


class RecordStore(Protocol):
    def save_adjudication(self, bundle: ReviewBundle) -> None: ...
    def all_bundles(self) -> list[ReviewBundle]: ...


class JsonlRecordStore:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._path = self._root / "adjudications.jsonl"

    def save_adjudication(self, bundle: ReviewBundle) -> None:
        existing = self._path.read_text() if self._path.exists() else ""
        new_content = existing + bundle.model_dump_json() + "\n"
        tmp = self._path.with_suffix(".jsonl.tmp")
        tmp.write_text(new_content)
        os.replace(tmp, self._path)  # atomic rename

    def all_bundles(self) -> list[ReviewBundle]:
        if not self._path.exists():
            return []
        return [
            ReviewBundle.model_validate_json(line)
            for line in self._path.read_text().splitlines()
            if line.strip()
        ]


def human_adjudicate(
    rec: ReviewRecommendation,
    dossier: ReviewDossier,
    synthesis_output: SynthesisOutput,
    decide: Callable[[ReviewRecommendation], ApprovalDecision],
) -> ReviewBundle | None:
    decision = decide(rec)
    if decision.action == "reject":
        return None
    verdict = Verdict(
        recommendation_id=rec.recommendation_id,
        adjudicated_status=decision.adjudicated_status or rec.review_status,
        approver=decision.approver,
        approved_at=datetime.now(timezone.utc),
        action=decision.action,
        note=decision.note,
    )
    return ReviewBundle(
        dossier=dossier,
        synthesis_output=synthesis_output,
        recommendation=rec,
        verdict=verdict,
    )
