"""Deterministic hashing. Raw-byte and canonical-JSON hashes answer different audit questions."""

from __future__ import annotations

import hashlib
import json


def canonical_json(obj: object) -> bytes:
    """Deterministic UTF-8 JSON: sorted keys, compact separators, no NaN/Infinity."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def evidence_hashes(
    raw_bytes: bytes, parsed: object, request_fingerprint: dict, normalization: dict
) -> tuple[str, str, str, str]:
    """Return (raw_payload_hash, canonical_payload_hash, request_fingerprint_hash, evidence_bundle_hash)."""
    raw_payload_hash = sha256_hex(raw_bytes)
    canonical_payload_hash = sha256_hex(canonical_json(parsed))
    rf_hash = sha256_hex(canonical_json(request_fingerprint))
    bundle = {
        "raw_payload_hash": raw_payload_hash,
        "canonical_payload_hash": canonical_payload_hash,
        "request_fingerprint": rf_hash,
        "normalization": normalization,
    }
    evidence_bundle_hash = sha256_hex(canonical_json(bundle))
    return raw_payload_hash, canonical_payload_hash, rf_hash, evidence_bundle_hash


_LINEAGE_COLUMNS = ("_dlt_load_id", "_dlt_id")


def strip_lineage(rows: list[dict]) -> list[dict]:
    """Drop dlt lineage columns so canonical hashing reflects content, not load identity."""
    return [{k: v for k, v in row.items() if k not in _LINEAGE_COLUMNS} for row in rows]


def oso_evidence(rows: list[dict], config_fingerprint: dict, run_ref: dict) -> tuple[str, str, str]:
    """Return (canonical_payload_hash, request_fingerprint, evidence_bundle_hash) for an OSO reading.

    canonical_payload_hash is a fetch-time record over lineage-stripped rows, never a cross-run
    equality oracle. request_fingerprint (config + window) plus the reduced value are the
    reproducibility anchor. evidence_bundle_hash folds in run_ref and is an opaque citation key.
    """
    canonical_payload_hash = sha256_hex(canonical_json(strip_lineage(rows)))
    request_fingerprint = sha256_hex(canonical_json(config_fingerprint))
    bundle = {
        "canonical_payload_hash": canonical_payload_hash,
        "request_fingerprint": request_fingerprint,
        "oso_run_ref": run_ref,
    }
    evidence_bundle_hash = sha256_hex(canonical_json(bundle))
    return canonical_payload_hash, request_fingerprint, evidence_bundle_hash
