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


def test_removed_manifest_reports_material_not_crash(tmp_path):
    """A manifest deleted in a PR must render a MATERIAL removal report, not raise.

    The workflow hands every changed registry/*.yaml path to validate_pr as `head`,
    including deleted ones. Before this, load_manifest raised FileNotFoundError and the
    whole static gate died — so a PR that retires a commitment could not go green.
    """
    from scripts.validate_pr import main, validate_removal

    base = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    ok, md = validate_removal(base, "registry/gone.yaml")
    assert ok is True
    assert "Manifest removed" in md
    assert "MATERIAL" in md
    assert "no longer monitored" in md

    # end-to-end through the CLI: nonexistent head + real base exits 0
    summary = tmp_path / "summary.md"
    rc = main(
        [
            "registry/definitely-not-here.yaml",
            "--base",
            "tests/fixtures/chainsafe_oso.yaml",
            "--summary",
            str(summary),
        ]
    )
    assert rc == 0
    assert "Manifest removed" in summary.read_text()


def test_missing_head_and_missing_base_still_fails():
    """Not a removal — a genuinely bogus invocation must stay a failure."""
    from scripts.validate_pr import main

    assert main(["registry/definitely-not-here.yaml"]) == 1
