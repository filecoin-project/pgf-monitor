import pytest

from fpm.manifest import ManifestError, load_manifest


def test_load_valid_manifest():
    m = load_manifest("tests/fixtures/chainsafe.yaml")
    assert m.team == "chainsafe"
    assert len(m.functions) == 2
    assert m.functions[0].sla.threshold_op == ">="
    assert m.functions[0].sla.threshold_value == 0.999
    assert m.functions[0].source.fixture == "forest_uptime.json"


def test_missing_functions_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("team: x\nmaintainers: [a]\n")
    with pytest.raises(ManifestError):
        load_manifest(bad)


def test_unknown_field_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "team: x\nmaintainers: [a]\nfunctions:\n"
        "  - function_id: f\n    tier: essential\n    typo: 1\n"
        "    sla: {statement: s, metric: m, threshold: {op: '>=', value: 1}, cadence: daily}\n"
        "    source: {adapter: fixture, fixture: x.json}\n"
    )
    with pytest.raises(ManifestError):
        load_manifest(bad)


def test_duplicate_function_id_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    fn = (
        "  - function_id: dup\n    tier: essential\n"
        "    sla: {statement: s, metric: m, threshold: {op: '>=', value: 1}, cadence: daily}\n"
        "    source: {adapter: fixture, fixture: x.json}\n"
    )
    bad.write_text("team: x\nmaintainers: [a]\nfunctions:\n" + fn + fn)
    with pytest.raises(ManifestError):
        load_manifest(bad)


def test_functions_carry_category_and_sub_category():
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    fn = m.functions[0]
    assert fn.category == "Coordination & Incentives"
    assert fn.sub_category == "Network data & monitoring"
