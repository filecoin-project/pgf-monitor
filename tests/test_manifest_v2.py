import pytest

from fpm.manifest import ManifestError, load_manifest


def test_load_http_json_manifest():
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    fn = m.functions[0]
    assert fn.source.adapter == "oso"
    assert fn.source.kind == "http-json"
    assert fn.source.base_url == "https://api.llama.fi"
    assert fn.source.query == "/v2/historicalChainTvl/Filecoin"
    assert fn.source.extract is not None
    assert fn.source.extract.column == "tvl"
    assert fn.source.extract.reduce == "latest"
    assert fn.source.extract.timestamp_column == "date"


def test_fixture_manifest_still_loads():
    m = load_manifest("tests/fixtures/chainsafe.yaml")
    assert m.functions[0].source.kind == "fixture"  # default when unspecified
    assert m.functions[0].source.fixture == "forest_uptime.json"


def test_http_json_requires_base_url_and_extract(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "team: x\nmaintainers: [a]\nfunctions:\n"
        "  - function_id: f\n    tier: important\n"
        "    sla: {statement: s, metric: m, threshold: {op: '>=', value: 1}, cadence: daily}\n"
        "    source: {adapter: oso, kind: http-json}\n"  # missing base_url, query, extract
    )
    with pytest.raises(ManifestError):
        load_manifest(bad)
