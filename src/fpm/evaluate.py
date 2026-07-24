"""Mechanical SLA evaluation. Provenance and identity are checked, not assumed."""

from __future__ import annotations

import operator

from fpm.domain import Reading, SlaResult
from fpm.manifest import FunctionSpec

_OPS = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt, "==": operator.eq}


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
    outcome = "pass" if _OPS[op](value, threshold) else "fail"
    return SlaResult(
        outcome=outcome,
        op=op,
        threshold=threshold,
        observed=value,
        measurement_window=window,
        reason=f"{value} {op} {threshold} is {outcome}",
    )
