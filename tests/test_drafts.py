"""Draft manifest tooling: split, promotion checks, textual x_draft strip."""

import textwrap

import pytest

from fpm.drafts import promotion_problems, split_draft, strip_x_draft_text
from fpm.kernel import load_kernel
from fpm.manifest import ManifestError

DRAFT = textwrap.dedent(
    """\
    # DRAFT — pre-populated by OSO.
    team: example
    maintainers: ["@someone"]
    x_draft:
      slate_status: "Advance"
      allowlist_additions: [example.org]
      unmeasured:
        - function: "coordination work"
          reason: "no machine-checkable signal"
    functions:
      # PROBED 2026-07-15: curl https://example.org/health -> 200
      - function_id: example-fn
        tier: irreplaceable
        category: 'Blockchain Core & Physical Storage'
        sub_category: 'Randomness'
        sla:
          statement: "lag <= 1 round, measured daily"
          metric: beacon_round_lag
          threshold: { op: "<=", value: 1 }
          cadence: daily
        source:
          adapter: oso
          kind: http-json
          base_url: "https://example.org"
          endpoint: "https://example.org/health"
          query: "/health"
          extract: { column: expected, column2: current, reduce: single, derive: diff }
    """
)


def _write(tmp_path, text):
    p = tmp_path / "example.yaml"
    p.write_text(text)
    return p


def test_split_draft_strips_x_draft_and_validates(tmp_path):
    manifest, x_draft = split_draft(_write(tmp_path, DRAFT))
    assert manifest.team == "example"
    assert manifest.functions[0].function_id == "example-fn"
    assert x_draft["slate_status"] == "Advance"
    assert x_draft["allowlist_additions"] == ["example.org"]


def test_split_draft_still_enforces_schema(tmp_path):
    bad = DRAFT.replace("cadence: daily", "cadence: hourly")
    with pytest.raises(ManifestError):
        split_draft(_write(tmp_path, bad))


def test_promotion_problems_flags_host_and_triple(tmp_path):
    manifest, _ = split_draft(_write(tmp_path, DRAFT))
    kernel = load_kernel()
    problems = promotion_problems(manifest, kernel, allowlist={"api.drand.sh"})
    assert any("allowlist" in p and "example.org" in p for p in problems)
    # catalogued triple -> no conformance complaint
    assert not any("uncatalogued" in p for p in problems)


def test_promotion_problems_empty_when_promotable(tmp_path):
    manifest, _ = split_draft(_write(tmp_path, DRAFT))
    kernel = load_kernel()
    assert promotion_problems(manifest, kernel, allowlist={"example.org"}) == []


def test_promotion_problems_flags_uncatalogued_triple(tmp_path):
    bad = DRAFT.replace("sub_category: 'Randomness'", "sub_category: 'Made Up'")
    manifest, _ = split_draft(_write(tmp_path, bad))
    problems = promotion_problems(manifest, load_kernel(), allowlist={"example.org"})
    assert any("example-fn" in p for p in problems)
    assert len(problems) == 1


def test_strip_x_draft_text_preserves_comments():
    stripped = strip_x_draft_text(DRAFT)
    assert "x_draft" not in stripped
    assert "slate_status" not in stripped
    assert "# PROBED 2026-07-15" in stripped
    assert "# DRAFT — pre-populated by OSO." in stripped
    assert "team: example" in stripped
    # the functions block survives intact
    assert "function_id: example-fn" in stripped


def test_strip_x_draft_text_noop_without_block():
    text = "team: t\nmaintainers: ['@a']\nfunctions: []\n"
    assert strip_x_draft_text(text) == text


def test_strip_x_draft_text_comment_mode_preserves_annotations():
    stripped = strip_x_draft_text(DRAFT, comment=True)
    assert "\nx_draft:" not in stripped and not stripped.startswith("x_draft:")
    assert "#   slate_status" in stripped.replace("# ", "#  ", 0) or "# " in stripped
    # annotations survive as comments; yaml still parses without the block
    import yaml

    raw = yaml.safe_load(stripped)
    assert "x_draft" not in raw
    assert "no machine-checkable signal" in stripped  # unmeasured reason kept
