from datetime import datetime, timezone

from fpm.manifest import load_manifest
from scripts.validate_pr import validate_manifest

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)


def test_catalogued_triple_passes_gate():
    head = load_manifest("tests/fixtures/chainsafe_oso.yaml")  # essential / Coord&Inc / Net data
    ok, md = validate_manifest(None, head, {"api.llama.fi"}, AS_OF)
    assert ok is True


def test_uncatalogued_triple_fails_gate():
    head = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    head.functions[0].sub_category = "made-up-subcat"
    ok, md = validate_manifest(None, head, {"api.llama.fi"}, AS_OF)
    assert ok is False
    assert "not a catalogued kernel slot" in md
