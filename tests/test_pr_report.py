from fpm.governance.classify import classify
from fpm.governance.diff import manifest_diff
from fpm.manifest import load_manifest
from scripts.pr_report import render_report


def test_report_flags_material_loosening():
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    m2 = m.model_copy(deep=True)
    m2.functions[0].sla.threshold_value = 1.0
    md = render_report(classify(manifest_diff(m, m2), m2))
    assert "MATERIAL" in md
    assert "loosened" in md
    assert "committee" in md.lower()


def test_report_trivial_only():
    m = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    md = render_report(classify(manifest_diff(m, m), m))
    assert "No changes" in md or "TRIVIAL" in md or "no material" in md.lower()
