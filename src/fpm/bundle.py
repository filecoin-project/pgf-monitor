"""The atomic adjudication unit: everything needed to audit what the model saw and decided."""

from __future__ import annotations

from fpm.domain import ReviewRecommendation, Verdict, _Model
from fpm.dossier import ReviewDossier
from fpm.synthesize import SynthesisOutput


class ReviewBundle(_Model):
    dossier: ReviewDossier
    synthesis_output: SynthesisOutput
    recommendation: ReviewRecommendation
    verdict: Verdict
