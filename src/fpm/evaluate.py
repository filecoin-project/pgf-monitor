"""Mechanical SLA evaluation. Provenance and identity are checked, not assumed.

Two separable jobs live here. `evaluate_sla` decides whether a reading is ADMISSIBLE —
identity, independent origin, evidence, a value at all — and only the pipeline can answer
that, because only the pipeline sees provenance. `meets_threshold` is the pure comparison,
which is also what the dashboard performs at render time against the thresholds time series.
"""

from __future__ import annotations

import operator

from fpm.domain import ComparisonOperator, Reading, SlaResult
from fpm.manifest import FunctionSpec

_OPS = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt, "==": operator.eq}


def meets_threshold(value: float, op: ComparisonOperator, threshold: float) -> bool:
    """The whole of the compliance rule. Kept separate so it can be reasoned about alone."""
    return bool(_OPS[op](value, threshold))


def evaluate_sla(reading: Reading, fn: FunctionSpec, team: str) -> SlaResult:
    op = fn.sla.threshold_op
    threshold = fn.sla.threshold_value
    window = reading.measurement_window

    def indeterminate(reason: str, observed: float | None = None) -> SlaResult:
        return SlaResult(
            outcome="indeterminate",
            op=op,
            threshold=threshold,
            observed=observed,
            measurement_window=window,
            reason=reason,
        )

    if reading.team != team:
        return indeterminate("reading team does not match manifest team")
    if reading.function_id != fn.function_id:
        return indeterminate("reading function does not match the SLA")
    if reading.metric != fn.sla.metric:
        return indeterminate("reading metric does not match the SLA metric")
    if reading.claim.origin != "independent":
        return indeterminate("reading is not an independently collected claim")
    if reading.claim.evidence is None:
        return indeterminate("independent reading lacks provenance evidence")
    if reading.claim.value is None:
        return indeterminate("no value in source response for the measurement window")

    value = reading.claim.value
    # Admissibility first, THEN the threshold: a dead source must read as indeterminate even
    # when no threshold is set, or a broken metric hides behind "nobody agreed a bar".
    if op is None or threshold is None:
        return SlaResult(
            outcome="unscored",
            op=op,
            threshold=threshold,
            observed=value,
            measurement_window=window,
            reason="no agreed threshold: measured, not scored",
        )

    outcome = "pass" if meets_threshold(value, op, threshold) else "fail"
    return SlaResult(
        outcome=outcome,
        op=op,
        threshold=threshold,
        observed=value,
        measurement_window=window,
        reason=f"{value} {op} {threshold} is {outcome}",
    )
