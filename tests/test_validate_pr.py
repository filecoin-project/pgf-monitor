from datetime import datetime, timezone

from fpm.domain import window_for  # noqa: F401  (import parity)
from fpm.manifest import load_manifest
from scripts.validate_pr import validate_manifest

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
ALLOW = {"api.llama.fi", "api.drand.sh", "filfox.info"}


def test_valid_manifest_passes():
    head = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    ok, md = validate_manifest(None, head, ALLOW, AS_OF)
    assert ok is True
    assert "Goalpost check" in md


def test_off_allowlist_base_url_fails():
    head = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    head.functions[0].source.base_url = "https://evil.example"
    ok, md = validate_manifest(None, head, ALLOW, AS_OF)
    assert ok is False
    assert "allowlist" in md.lower()


def test_material_loosening_surfaces_in_report():
    base = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    head = base.model_copy(deep=True)
    head.functions[0].sla.threshold_value = 1.0
    ok, md = validate_manifest(base, head, ALLOW, AS_OF)
    assert ok is True  # a loosening is not a *validation* failure; it is a committee flag
    assert "MATERIAL" in md and "loosened" in md
