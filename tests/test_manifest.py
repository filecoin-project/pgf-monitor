import pytest

from fpm.manifest import ManifestError, load_manifest, manifest_from_raw


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


def _raw_function(**sla_overrides):
    sla = {
        "statement": "release cadence stays under 90 days",
        "metric": "release_age_days",
        "threshold": {"op": "<=", "value": 90.0},
        "cadence": "daily",
    }
    sla.update(sla_overrides)
    return {
        "team": "acme",
        "maintainers": ["acme-bot"],
        "functions": [
            {
                "function_id": "acme-release-cadence",
                "tier": "essential",
                "category": "UX/DX",
                "sub_category": "Tooling",
                "sla": sla,
                "source": {"adapter": "fixture", "kind": "fixture", "fixture": "acme.json"},
            }
        ],
    }


def test_manifest_without_a_threshold_loads_unscored():
    raw = _raw_function()
    del raw["functions"][0]["sla"]["threshold"]
    sla = manifest_from_raw(raw).functions[0].sla
    assert sla.threshold_op is None
    assert sla.threshold_value is None
    assert sla.threshold_source == "provisional"


def test_threshold_source_defaults_to_provisional():
    sla = manifest_from_raw(_raw_function()).functions[0].sla
    assert (sla.threshold_op, sla.threshold_value) == ("<=", 90.0)
    assert sla.threshold_source == "provisional"


def test_threshold_source_is_read_from_the_manifest():
    raw = _raw_function(threshold={"op": "<=", "value": 90.0, "source": "signed-appendix"})
    assert manifest_from_raw(raw).functions[0].sla.threshold_source == "signed-appendix"


def test_a_threshold_still_needs_both_op_and_value():
    raw = _raw_function(threshold={"op": "<="})
    with pytest.raises(ManifestError):
        manifest_from_raw(raw)
