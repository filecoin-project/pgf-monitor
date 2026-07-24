"""Offline adapter that reads canned response bytes. No network. Skeleton + tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fpm.domain import Claim, EvidenceRef, MeasurementWindow, Reading
from fpm.hashing import evidence_hashes
from fpm.manifest import FunctionSpec


def _declared_window_days(payload: dict) -> int | None:
    win = payload.get("window")
    if isinstance(win, str) and win.endswith("d") and win[:-1].isdigit():
        return int(win[:-1])
    return None


class FixtureAdapter:
    name = "fixture"
    version = "0.1.0"

    def __init__(self, fixtures_dir: Path) -> None:
        self._dir = Path(fixtures_dir)

    def fetch(self, fn: FunctionSpec, team: str, window: MeasurementWindow) -> Reading:
        raw_bytes = (self._dir / fn.source.fixture).read_bytes()
        payload = json.loads(raw_bytes)
        request_fingerprint = {
            "endpoint": fn.source.endpoint,
            "query": fn.source.query,
            "adapter_version": self.version,
            "window_start": window.start.isoformat(),
            "window_end": window.end.isoformat(),
        }
        raw_h, canon_h, rf_h, bundle_h = evidence_hashes(
            raw_bytes, payload, request_fingerprint, {"metric": fn.sla.metric}
        )
        value = payload.get("value")
        source_metadata = {}
        days = _declared_window_days(payload)
        if days is not None:
            source_metadata["declared_window_days"] = days
        claim = Claim(
            value=float(value) if value is not None else None,
            origin="independent",
            source_ref=fn.source.endpoint,
            fetched_at=datetime.now(timezone.utc),
            evidence=EvidenceRef(
                raw_payload_hash=raw_h,
                canonical_payload_hash=canon_h,
                request_fingerprint=rf_h,
                evidence_bundle_hash=bundle_h,
            ),
            fetched_by=f"{self.name}@{self.version}",
        )
        return Reading(
            team=team,
            function_id=fn.function_id,
            metric=fn.sla.metric,
            measurement_window=window,
            claim=claim,
            source_metadata=source_metadata,
            adapter=self.name,
            adapter_version=self.version,
        )
