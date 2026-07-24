from fpm.hashing import canonical_json, oso_evidence, sha256_hex, strip_lineage


def test_strip_lineage_drops_dlt_columns():
    rows = [
        {"tvl": 1, "_dlt_load_id": "x", "_dlt_id": "y"},
        {"tvl": 2, "_dlt_load_id": "x", "_dlt_id": "z"},
    ]
    assert strip_lineage(rows) == [{"tvl": 1}, {"tvl": 2}]


def test_oso_evidence_canonical_ignores_lineage():
    rows_a = [{"tvl": 1, "_dlt_load_id": "load-1", "_dlt_id": "a"}]
    rows_b = [
        {"tvl": 1, "_dlt_load_id": "load-2", "_dlt_id": "b"}
    ]  # same content, different lineage
    cfg = {"base_url": "u", "window_end": "2026-07-01"}
    canon_a, rf_a, _ = oso_evidence(rows_a, cfg, {"run_id": "r1"})
    canon_b, rf_b, _ = oso_evidence(rows_b, cfg, {"run_id": "r2"})
    assert canon_a == canon_b  # lineage stripped -> canonical payload identical
    assert rf_a == rf_b  # same config fingerprint


def test_oso_evidence_bundle_folds_run_ref():
    rows = [{"tvl": 1}]
    cfg = {"base_url": "u"}
    _, _, bundle1 = oso_evidence(rows, cfg, {"run_id": "r1"})
    _, _, bundle2 = oso_evidence(rows, cfg, {"run_id": "r2"})
    assert bundle1 != bundle2  # run ref makes the bundle unique per run
    assert len(bundle1) == 64


def test_request_fingerprint_is_config_hash():
    rows = [{"tvl": 1}]
    _, rf, _ = oso_evidence(rows, {"base_url": "u"}, {"run_id": "r"})
    assert rf == sha256_hex(canonical_json({"base_url": "u"}))
