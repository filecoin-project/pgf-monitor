from __future__ import annotations

from typing import Protocol, runtime_checkable

from fpm.domain import DetectorResult, Flag, Reading, _Model
from fpm.manifest import FunctionSpec


class DetectorContract(_Model):
    detector_id: str
    applicable_metrics: list[str]
    version: str
    output_flag_type: str


@runtime_checkable
class Detector(Protocol):
    contract: DetectorContract

    def run(self, reading: Reading, fn: FunctionSpec) -> DetectorResult: ...


class DetectorRegistry:
    def __init__(self, detectors: list[Detector]) -> None:
        self._detectors = list(detectors)

    def results(self, reading: Reading, fn: FunctionSpec) -> list[DetectorResult]:
        # Detector isolation: a detector that raises (e.g. a corroboration query against a
        # missing table) must not abort the function's review. Detectors are indicators,
        # not determinations — an errored one reports insufficient_data with the error.
        out: list[DetectorResult] = []
        for d in self._detectors:
            try:
                out.append(d.run(reading, fn))
            except Exception as exc:
                out.append(
                    DetectorResult(
                        detector_id=d.contract.detector_id,
                        detector_version=d.contract.version,
                        signal="insufficient_data",
                        note=f"detector error: {exc}"[:300],
                    )
                )
        return out

    def flags(self, results: list[DetectorResult]) -> list[Flag]:
        out: list[Flag] = []
        by_id = {d.contract.detector_id: d for d in self._detectors}
        for r in results:
            if r.signal == "signal_detected":
                contract = by_id[r.detector_id].contract
                out.append(
                    Flag(
                        flag_id=f"{r.detector_id}:{'|'.join(r.evidence_refs) or 'noref'}",
                        detector_id=r.detector_id,
                        type=contract.output_flag_type,
                        severity="medium",
                        evidence_refs=r.evidence_refs,
                        note=r.note,
                    )
                )
        return out

    def versions(self) -> dict[str, str]:
        return {d.contract.detector_id: d.contract.version for d in self._detectors}


def _default_registry() -> DetectorRegistry:
    from fpm.detectors.window import WindowDetector

    return DetectorRegistry([WindowDetector()])


DETECTORS = _default_registry()
