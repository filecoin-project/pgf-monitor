"""The static gate runs scripts.validate_pr — the ADOPTED-manifest validator — over the
registry files a PR changed. Drafts must not be selected: they legitimately carry an `x_draft`
block that `_schema.json` forbids, so feeding one to validate_pr fails the gate with
"Additional properties are not allowed ('x_draft' was unexpected)".

That is not hypothetical. Git's DEFAULT pathspec lets `*` cross `/`, so a bare
'registry/*.yaml' matches registry/drafts/<team>.yaml. The bug shipped in the repo's first
commit and lay dormant until the first PR to touch a draft, which it failed. `:(glob)` magic
confines `*` to one path segment, which is what makes the selection mean what it reads as.

Drafts are still validated — by scripts/validate_draft.py and tests/test_drafts_conformance.py,
both of which strip x_draft first.
"""

import re
from pathlib import Path

WORKFLOW = Path(".github/workflows/validate.yml")

# The line that picks which changed registry files the adopted-manifest gate will validate.
_SELECT_RE = re.compile(r"^\s*changed=\$\(git diff --name-only.*?--\s*(?P<pathspec>\S+)", re.M)


def _selection_pathspec() -> str:
    m = _SELECT_RE.search(WORKFLOW.read_text())
    assert m, "could not find the changed-manifest selection line in validate.yml"
    return m.group("pathspec").strip("'\"")


def test_workflow_exists():
    assert WORKFLOW.is_file()


def test_gate_pathspec_cannot_reach_drafts():
    pathspec = _selection_pathspec()
    assert pathspec.startswith(":(glob)"), (
        f"gate selects with {pathspec!r}; without :(glob) magic git lets '*' cross '/', so "
        "registry/drafts/<team>.yaml is handed to validate_pr and the gate fails on x_draft"
    )


def test_gate_pathspec_still_targets_registry_yaml():
    # Guard against 'fixing' the above by narrowing the gate into uselessness.
    assert _selection_pathspec() == ":(glob)registry/*.yaml"
