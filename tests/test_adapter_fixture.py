from datetime import datetime, timezone
from pathlib import Path

import pytest

from fpm.adapters.registry import UnsupportedAdapterError, build_adapters
from fpm.domain import window_for
from fpm.manifest import load_manifest

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _adapter():
    return build_adapters(Path("fixtures/responses"))["fixture"]


def _fn(idx):
    return load_manifest("tests/fixtures/chainsafe.yaml").functions[idx]


def test_fetch_value_hashes_window_and_metadata():
    fn = _fn(0)
    reading = _adapter().fetch(fn, "chainsafe", window_for(fn.sla.cadence, AS_OF))
    assert reading.claim.value == 0.9993
    assert reading.claim.origin == "independent"
    assert reading.claim.evidence is not None
    assert len(reading.claim.evidence.raw_payload_hash) == 64
    assert reading.claim.evidence.raw_payload_hash != reading.claim.evidence.canonical_payload_hash
    assert reading.measurement_window.end == AS_OF
    assert reading.source_metadata["declared_window_days"] == 30


def test_missing_value_is_none_but_provenance_present():
    fn = _fn(1)
    reading = _adapter().fetch(fn, "chainsafe", window_for(fn.sla.cadence, AS_OF))
    assert reading.claim.value is None
    assert reading.claim.evidence is not None


def test_unknown_adapter_raises():
    with pytest.raises(UnsupportedAdapterError):
        build_adapters(Path("fixtures/responses"))["grafana"]
