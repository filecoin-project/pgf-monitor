"""`repos`: the GitHub repositories a funded commitment covers, and the check that they agree.

Two facts used to share one field. `funded_project_oso_slug` says WHO is paid (an OSO project
slug); `repos` says WHAT code the work covers. Conflating them is why a slug audit found our
values split three ways between funded teams, team orgs and code repositories.

Repos are stored as lowercase `owner/name` because that is OSO's GITHUB_REPO artifact identity:
`filpgf_public.artifacts_by_project.artifact_name` holds the full `namespace/name` in lowercase,
so a list in this shape joins to the mart with no lookup table. A mixed-case owner would miss.
"""

from __future__ import annotations

import re

from fpm.manifest import FunctionSpec

#: lowercase `owner/name`, one slash
REPO_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*$")

#: a GitHub REST path naming a repository, e.g. /repos/ChainSafe/forest/releases
_SOURCE_REPO = re.compile(r"/repos/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")


def repo_from_source(fn: FunctionSpec) -> str | None:
    """The repository this function's source fetches, lowercased, or None if it fetches none."""
    match = _SOURCE_REPO.search(f"{fn.source.base_url}{fn.source.query}")
    return f"{match.group(1).lower()}/{match.group(2).lower()}" if match else None


def repo_shape_errors(repos: list[str]) -> list[str]:
    return [f"repo {r!r} is not a lowercase owner/name" for r in repos if not REPO_PATTERN.match(r)]


def source_repo_error(fn: FunctionSpec) -> str | None:
    """None unless the source names a repository the entry does not enumerate.

    A metric repointed at a different repository without the enumeration following would otherwise
    keep reporting under the old code's name.
    """
    repo = repo_from_source(fn)
    if repo is None or repo in fn.repos:
        return None
    listed = ", ".join(fn.repos) if fn.repos else "nothing"
    return (
        f"source fetches {repo!r} but repos lists {listed}; add it, or repoint the source "
        "if the enumeration is the correct one"
    )
