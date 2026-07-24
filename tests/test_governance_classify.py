from fpm.governance.classify import classify, has_material
from fpm.governance.diff import manifest_diff
from fpm.manifest import load_manifest


def _with_threshold(m, value, op=None):
    m2 = m.model_copy(deep=True)
    m2.functions[0].sla.threshold_value = value
    if op:
        m2.functions[0].sla.threshold_op = op
    return m2


def test_loosening_ge_threshold():
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")  # chain_tvl_usd >= 1_000_000
    m2 = _with_threshold(m, 1.0)  # lower the bar
    items = classify(manifest_diff(m, m2), m2)
    tv = next(i for i in items if i.field_path == "sla.threshold_value")
    assert tv.bucket == "material" and tv.direction == "loosened"
    assert has_material(items)


def test_tightening_ge_threshold():
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    m2 = _with_threshold(m, 9_000_000.0)  # raise the bar
    tv = next(
        i for i in classify(manifest_diff(m, m2), m2) if i.field_path == "sla.threshold_value"
    )
    assert tv.direction == "tightened"


def test_statement_is_trivial():
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    m2 = m.model_copy(deep=True)
    m2.functions[0].sla.statement = "reworded"
    items = classify(manifest_diff(m, m2), m2)
    assert all(i.bucket == "trivial" for i in items)
    assert not has_material(items)


def test_reduce_change_is_material_direction_unknown():
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    m2 = m.model_copy(deep=True)
    m2.functions[0].source.extract.reduce = "avg"
    it = next(
        i for i in classify(manifest_diff(m, m2), m2) if i.field_path == "source.extract.reduce"
    )
    assert it.bucket == "material" and it.direction == "n/a"
