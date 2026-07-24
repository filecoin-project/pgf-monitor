import math

import pytest

from fpm.hashing import canonical_json, evidence_hashes, sha256_hex


def test_canonical_json_key_order_independent():
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})


def test_canonical_json_rejects_nan():
    with pytest.raises(ValueError):
        canonical_json({"x": math.nan})


def test_sha256_hex_shape():
    assert len(sha256_hex(b"abc")) == 64


def test_evidence_hashes_distinguish_raw_and_canonical():
    raw = b'{"b": 1, "a": 2}'
    parsed = {"a": 2, "b": 1}
    raw_h, canon_h, rf_h, bundle_h = evidence_hashes(raw, parsed, {"q": "x"}, {"n": 1})
    # raw bytes hash differs from canonical hash (whitespace/order differ)
    assert raw_h == sha256_hex(raw)
    assert canon_h == sha256_hex(canonical_json(parsed))
    assert raw_h != canon_h
    # bundle changes if the request changes
    _, _, rf2, bundle2 = evidence_hashes(raw, parsed, {"q": "y"}, {"n": 1})
    assert rf_h != rf2 and bundle_h != bundle2
