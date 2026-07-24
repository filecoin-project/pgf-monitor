from fpm.governance.classify import classify
from fpm.governance.diff import manifest_diff
from fpm.manifest import TransformSpec, load_manifest


def _mutate(m, **fnkw):
    m2 = m.model_copy(deep=True)
    for k, v in fnkw.items():
        setattr(m2.functions[0].sla, k, v)
    return m2


def test_no_change_empty_diff():
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    assert manifest_diff(m, m) == []


def test_threshold_change_detected():
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    m2 = _mutate(m, threshold_value=0.5)
    changes = manifest_diff(m, m2)
    paths = {(c.field_path, c.kind) for c in changes}
    assert ("sla.threshold_value", "modified") in paths
    c = next(c for c in changes if c.field_path == "sla.threshold_value")
    assert c.function_id == m.functions[0].function_id
    assert c.old == m.functions[0].sla.threshold_value and c.new == 0.5


def test_added_and_removed_functions():
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    fewer = m.model_copy(deep=True)
    fewer.functions = m.functions[:0] if len(m.functions) == 1 else m.functions[:-1]
    # removed: old has functions the new lacks
    changes = manifest_diff(m, fewer)
    assert any(c.kind == "removed" and c.field_path == "function" for c in changes)
    # added: reverse
    changes2 = manifest_diff(fewer, m)
    assert any(c.kind == "added" and c.field_path == "function" for c in changes2)


def test_maintainers_change_detected():
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    m2 = m.model_copy(deep=True)
    m2.maintainers = m.maintainers + ["@new"]
    changes = manifest_diff(m, m2)
    assert any(c.field_path == "maintainers" for c in changes)


def test_adapter_swap_detected():
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    m2 = m.model_copy(deep=True)
    m2.functions[0].source.adapter = "fixture"
    changes = manifest_diff(m, m2)
    assert any(c.field_path == "source.adapter" and c.kind == "modified" for c in changes)


def _with_transform(m, sql):
    m2 = m.model_copy(deep=True)
    m2.functions[0].source.extract = None
    m2.functions[0].transform = TransformSpec(sql=sql)
    return m2


def test_transform_sql_change_is_material():
    m = _with_transform(
        load_manifest("tests/fixtures/chainsafe_oso.yaml"), "SELECT avg(v) FROM raw"
    )
    m2 = _with_transform(
        load_manifest("tests/fixtures/chainsafe_oso.yaml"), "SELECT max(v) FROM raw"
    )
    changes = manifest_diff(m, m2)
    assert any(c.field_path == "source.transform.sql" and c.kind == "modified" for c in changes)
    classified = classify(changes, m2)
    assert any(
        c.field_path == "source.transform.sql" and c.bucket == "material" for c in classified
    )


def test_extract_to_transform_swap_detected():
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")  # uses extract
    m2 = _with_transform(m, "SELECT avg(v) FROM raw")
    changes = manifest_diff(m, m2)
    paths = {c.field_path for c in changes}
    assert "source.transform.sql" in paths  # transform appeared
    assert any(p.startswith("source.extract.") for p in paths)  # extract fields dropped


def test_category_change_detected():
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    m2 = m.model_copy(deep=True)
    m2.functions[0].sub_category = "Explorers and Tooling"
    changes = manifest_diff(m, m2)
    assert any(c.field_path == "sub_category" for c in changes)
