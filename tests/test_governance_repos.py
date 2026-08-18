"""`repos` enumerates the code the funded work covers, and must agree with what we fetch.

Fifteen metrics read a GitHub repository directly, so their source URL already names one. If the
enumeration and the URL disagree, one of them is wrong about what is being measured; the cheap,
offline check is to require the URL's repo to appear in the list.
"""

from __future__ import annotations

from fpm.governance.repos import (
    REPO_PATTERN,
    repo_from_source,
    repo_shape_errors,
    source_repo_error,
)
from fpm.manifest import FunctionSpec, SlaSpec, SourceSpec


def _fn(query="", base="https://api.github.com", repos=None):
    return FunctionSpec(
        function_id="probe",
        kernel_id="chain-sync-state",
        tier="essential",
        category="Blockchain Core & Physical Storage",
        sub_category="Ledger & Consensus",
        funded_project_oso_slug="drand",
        repos=repos or [],
        sla=SlaSpec(statement="s", metric="m", cadence="daily"),
        source=SourceSpec(adapter="oso", kind="http-json", base_url=base, query=query),
    )


def test_repo_is_read_out_of_the_source_url_lowercased():
    """OSO stores GITHUB_REPO artifact_name lowercased, and that column is the join key, so a
    mixed-case owner has to be normalized or the join silently misses."""
    assert repo_from_source(_fn(query="/repos/ChainSafe/forest/releases")) == "chainsafe/forest"


def test_no_repo_in_the_url_is_not_an_error():
    assert repo_from_source(_fn(base="https://filfox.info", query="/api/v1/tipset/recent")) is None
    assert source_repo_error(_fn(base="https://filfox.info", query="/api/v1/x")) is None


def test_a_source_repo_missing_from_the_enumeration_is_an_error():
    err = source_repo_error(_fn(query="/repos/ChainSafe/forest/releases", repos=["drand/drand"]))
    assert err and "chainsafe/forest" in err


def test_a_source_repo_present_in_the_enumeration_is_fine():
    assert (
        source_repo_error(_fn(query="/repos/ChainSafe/forest/releases", repos=["chainsafe/forest"]))
        is None
    )


def test_repo_shape_must_be_lowercase_owner_slash_name():
    assert repo_shape_errors(["chainsafe/forest"]) == []
    assert repo_shape_errors(["ChainSafe/forest"]), "uppercase must be rejected"
    assert repo_shape_errors(["forest"]), "a bare name must be rejected"
    assert repo_shape_errors(["a/b/c"]), "more than one slash must be rejected"
    assert REPO_PATTERN.match("ipfs-force-community/sophon-miner")
