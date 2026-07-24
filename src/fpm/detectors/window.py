"""Structural check: does the fetched measurement window match the SLA cadence?"""

from __future__ import annotations

from fpm.detectors.base import DetectorContract
from fpm.domain import DetectorResult, Reading
from fpm.manifest import FunctionSpec

_CADENCE_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}


class WindowDetector:
    contract = DetectorContract(
        detector_id="window-vs-cadence",
        applicable_metrics=["uptime_ratio"],
        version="0.1.0",
        output_flag_type="window_mismatch",
    )

    def run(self, reading: Reading, fn: FunctionSpec) -> DetectorResult:
        det_id, ver = self.contract.detector_id, self.contract.version
        if fn.sla.metric not in self.contract.applicable_metrics:
            return DetectorResult(detector_id=det_id, detector_version=ver, signal="not_applicable")
        declared = reading.source_metadata.get("declared_window_days")
        if declared is None:
            return DetectorResult(
                detector_id=det_id,
                detector_version=ver,
                signal="insufficient_data",
                note="no declared window to inspect",
            )
        expected = _CADENCE_DAYS[fn.sla.cadence]
        refs = [reading.claim.evidence.evidence_bundle_hash] if reading.claim.evidence else []
        if declared != expected:
            return DetectorResult(
                detector_id=det_id,
                detector_version=ver,
                signal="signal_detected",
                evidence_refs=refs,
                note=f"declared window {declared}d != cadence {expected}d",
            )
        return DetectorResult(
            detector_id=det_id,
            detector_version=ver,
            signal="no_signal",
            evidence_refs=refs,
            note="declared window consistent with cadence",
        )
