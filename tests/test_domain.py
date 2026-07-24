from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from fpm.domain import (
    Claim,
    EvidenceRef,
    MeasurementWindow,
    make_recommendation_id,
    window_for,
)

H = "a" * 64
AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _evidence():
    return EvidenceRef(
        raw_payload_hash=H,
        canonical_payload_hash=H,
        request_fingerprint=H,
        evidence_bundle_hash=H,
    )


def test_hash_type_rejects_non_hex():
    with pytest.raises(ValidationError):
        EvidenceRef(
            raw_payload_hash="nope",
            canonical_payload_hash=H,
            request_fingerprint=H,
            evidence_bundle_hash=H,
        )


def test_claim_requires_datetime():
    c = Claim(
        value=1.0,
        origin="independent",
        source_ref="s",
        fetched_at=AS_OF,
        evidence=_evidence(),
        fetched_by="f",
    )
    assert c.fetched_at == AS_OF


def test_origin_constrained():
    with pytest.raises(ValidationError):
        Claim(
            value=1.0,
            origin="made-up",
            source_ref="s",
            fetched_at=AS_OF,
            evidence=None,
            fetched_by="f",
        )


def test_window_for_monthly():
    w = window_for("monthly", AS_OF)
    assert w.end == AS_OF
    assert w.start == AS_OF - timedelta(days=30)


def test_recommendation_id_is_stable():
    a = make_recommendation_id("chainsafe", "network-uptime", AS_OF, "deadbeef")
    b = make_recommendation_id("chainsafe", "network-uptime", AS_OF, "deadbeef")
    assert a == b and "chainsafe" in a and "deadbeef" in a


def test_measurement_window_roundtrips():
    w = MeasurementWindow(start=AS_OF, end=AS_OF)
    assert MeasurementWindow.model_validate_json(w.model_dump_json()) == w


def test_evidence_ref_allows_null_raw_hash():
    ev = EvidenceRef(
        raw_payload_hash=None,
        canonical_payload_hash=H,
        request_fingerprint=H,
        evidence_bundle_hash=H,
    )
    assert ev.raw_payload_hash is None
