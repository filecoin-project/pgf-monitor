from datetime import datetime, timezone

from fpm.manifest import TransformSpec, load_manifest
from scripts.validate_pr import validate_manifest

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _head(sql):
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    m.functions[0].source.extract = None
    m.functions[0].transform = TransformSpec(sql=sql)
    return m


def test_valid_transform_passes_gate():
    head = _head("SELECT avg(tvl) FROM raw")
    ok, md = validate_manifest(None, head, {"api.llama.fi"}, AS_OF)
    assert ok is True


def test_foreign_table_transform_fails_gate():
    head = _head("SELECT count(*) FROM oso.projects_v1")
    ok, md = validate_manifest(None, head, {"api.llama.fi"}, AS_OF)
    assert ok is False
    assert "transform" in md.lower()
