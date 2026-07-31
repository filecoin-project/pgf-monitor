"""The root SKILL.md is the zero-setup agent entry point: agents fetch it by raw URL and
follow its links without cloning. That only works if every raw-URL path it cites still
exists, so this guards against silent link rot when a doc moves. Path existence only — no
network."""

import re
from pathlib import Path

import pytest

SKILL = Path("SKILL.md")
README = Path("README.md")
RAW_BASE = "https://raw.githubusercontent.com/filecoin-project/pgf-monitor/main"

# Matches both the fully-qualified raw URL and the $BASE/... shorthand the file defines.
_PATH_RE = re.compile(r"(?:" + re.escape(RAW_BASE) + r"|\$BASE|\$\{BASE\})/([A-Za-z0-9._/-]+)")


def _cited_paths() -> list[str]:
    text = SKILL.read_text()
    # Placeholder paths like registry/<team>.yaml are not literal files. The character class
    # above excludes '<', so such a citation truncates to a bare directory ("registry/");
    # dropping anything with a trailing slash discards those without hiding real misses.
    found = (m for m in _PATH_RE.findall(text) if not m.endswith("/"))
    return sorted(set(found))


def test_skill_md_exists():
    assert SKILL.is_file()


def test_skill_md_cites_some_paths():
    # A guard that guards nothing would pass silently forever.
    assert len(_cited_paths()) >= 4


@pytest.mark.parametrize("rel", _cited_paths() if SKILL.is_file() else [], ids=lambda r: r)
def test_cited_path_exists(rel):
    assert Path(rel).exists(), f"SKILL.md cites {rel!r}, which is not in the repo"


def test_readme_points_at_skill_md():
    assert "SKILL.md" in README.read_text()


def test_raw_base_pinned_in_skill_md_and_readme():
    # Every citation in SKILL.md uses the $BASE shorthand, so _PATH_RE's fully-qualified
    # RAW_BASE branch never actually matches anything there. If the repo slug on SKILL.md's
    # `BASE=` line ever drifted (or the line were deleted), every $BASE/... citation would
    # 404 while this whole test module stayed green. Pin the literal string in both files so
    # that drift fails loudly instead.
    assert RAW_BASE in SKILL.read_text(), f"SKILL.md no longer defines BASE as {RAW_BASE!r}"
    assert RAW_BASE in README.read_text(), f"README.md no longer links the raw repo at {RAW_BASE!r}"
