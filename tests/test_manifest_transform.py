import pytest

from fpm.manifest import ManifestError, load_manifest

_HEAD = (
    "team: x\nmaintainers: [a]\nfunctions:\n  - function_id: f\n    kernel_id: chain-sync-state\n"
    "    funded_project_oso_slug: drand\n    tier: essential\n"
    "    category: 'UX/DX'\n    sub_category: 'Explorers and Tooling'\n"
)
_SLA = "    sla: {statement: s, metric: m, threshold: {op: '<=', value: 500}, cadence: daily}\n"


def _write(tmp_path, source_and_transform):
    p = tmp_path / "m.yaml"
    p.write_text(_HEAD + _SLA + source_and_transform)
    return p


def test_transform_parses(tmp_path):
    p = _write(
        tmp_path,
        "    source: {adapter: oso, kind: http-json, base_url: 'https://x.io', query: /q}\n"
        "    transform: {sql: 'SELECT avg(v) FROM raw'}\n",
    )
    fn = load_manifest(p).functions[0]
    assert fn.transform is not None
    assert fn.transform.sql == "SELECT avg(v) FROM raw"
    assert fn.source.extract is None


def test_both_extract_and_transform_rejected(tmp_path):
    p = _write(
        tmp_path,
        "    source:\n"
        "      adapter: oso\n      kind: http-json\n      base_url: 'https://x.io'\n      query: /q\n"
        "      extract: {column: v}\n"
        "    transform: {sql: 'SELECT avg(v) FROM raw'}\n",
    )
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_http_json_with_neither_rejected(tmp_path):
    p = _write(
        tmp_path,
        "    source: {adapter: oso, kind: http-json, base_url: 'https://x.io', query: /q}\n",
    )
    with pytest.raises(ManifestError):
        load_manifest(p)
