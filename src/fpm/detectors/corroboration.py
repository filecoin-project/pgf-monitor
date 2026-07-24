"""Corroboration detector: compare a team's ingested value against an independent OSO signal.

Output is an indicator, not a determination. Divergence beyond a fractional tolerance raises a
flag with evidence for human adjudication; it never auto-fails the SLA.
"""

from __future__ import annotations

from fpm.detectors.base import DetectorContract, DetectorRegistry
from fpm.detectors.window import WindowDetector
from fpm.domain import DetectorResult, Reading
from fpm.manifest import FunctionSpec
from fpm.oso.client import OsoIngestionClient


class CorroborationDetector:
    contract = DetectorContract(
        detector_id="corroboration-vs-independent",
        applicable_metrics=["chain_tvl_usd"],
        version="0.1.0",
        output_flag_type="corroboration_divergence",
    )

    def __init__(
        self,
        client: OsoIngestionClient,
        corroboration_sql: str,
        value_column: str,
        tolerance: float = 0.2,
    ) -> None:
        self._client = client
        self._sql = corroboration_sql
        self._col = value_column
        self._tolerance = tolerance

    def run(self, reading: Reading, fn: FunctionSpec) -> DetectorResult:
        det_id, ver = self.contract.detector_id, self.contract.version
        if fn.sla.metric not in self.contract.applicable_metrics:
            return DetectorResult(detector_id=det_id, detector_version=ver, signal="not_applicable")
        claimed = reading.claim.value
        rows = self._client.query(self._sql)
        corroborating = rows[0][self._col] if rows and self._col in rows[0] else None
        if claimed is None or corroborating is None:
            return DetectorResult(
                detector_id=det_id,
                detector_version=ver,
                signal="insufficient_data",
                note="missing claimed or corroborating value",
            )
        refs = [reading.claim.evidence.evidence_bundle_hash] if reading.claim.evidence else []
        denom = abs(float(corroborating)) or 1.0
        divergence = abs(float(claimed) - float(corroborating)) / denom
        if divergence > self._tolerance:
            return DetectorResult(
                detector_id=det_id,
                detector_version=ver,
                signal="signal_detected",
                evidence_refs=refs,
                note=f"claimed {claimed} vs independent {corroborating} (>{self._tolerance:.0%})",
            )
        return DetectorResult(
            detector_id=det_id,
            detector_version=ver,
            signal="no_signal",
            evidence_refs=refs,
            note="claimed value corroborated",
        )


def build_detectors(oso_client: OsoIngestionClient | None = None) -> DetectorRegistry:
    detectors = [WindowDetector()]
    if oso_client is not None:
        detectors.append(
            CorroborationDetector(
                oso_client,
                corroboration_sql="SELECT tvl AS v FROM oso.filecoin_tvl_independent LIMIT 1",
                value_column="v",
            )
        )
    return DetectorRegistry(detectors)
