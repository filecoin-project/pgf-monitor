"""fpm contract: render §1–§5 appendix template from manifest + facts."""

import yaml

from fpm.kernel import load_kernel
from fpm.manifest import manifest_from_raw
from fpm.report.contract import build_contract


def _fn(fid, tier, sub, metric, *, kernel_function=""):
    fn = {
        "function_id": fid,
        "tier": tier,
        "category": "Blockchain Core & Physical Storage",
        "sub_category": sub,
        "sla": {
            "statement": f"{fid} holds",
            "metric": metric,
            "threshold": {"op": "<=", "value": 1},
            "cadence": "daily",
        },
        "source": {
            "adapter": "oso",
            "kind": "http-json",
            "base_url": "https://x.test",
            "query": "/q",
            "endpoint": "https://x.test/q",
            "extract": {"column": "c"},
        },
    }
    if kernel_function:
        fn["kernel_function"] = kernel_function
    return fn


_RAW = {
    "team": "t",
    "maintainers": ["@m"],
    "functions": [
        _fn("relay-liveness", "essential", "Randomness", "relay_lag"),
        _fn("beacon", "irreplaceable", "Randomness", "beacon_lag"),
        _fn("rpc-head-lag", "essential", "Ledger & Consensus", "head_lag"),
        _fn("statuspage", "essential", "Randomness", "statuspage_impact_level"),
    ],
}

_FACTS = {
    "recipient": "Test Team",
    "contact": "c",
    "app_ref": "APP-T",
    "scope": "s",
    "committed_usd": 1000,
    "committed_through": "2026-12-31",
    "total_requested_usd": 2000,
    "term": "term",
    "repo_url": "https://github.com/filecoin-project/pgf-monitor",
    "incident_response": {"slas": ["statuspage"], "lead_in": "Sourced as follows:"},
    "placeholder_thresholds": ["relay-liveness"],
    "requested_additions": [
        {
            "metric": "threshold_signers_per_round",
            "statement": "How many nodes contribute to each signing round",
        },
    ],
    "dependents": [
        {"name": "Lotus", "how": "reads the beacon", "contact": "FilOz"},
    ],
    "dependencies": [
        {
            "name": "League of Entropy",
            "breaks": "no randomness",
            "owner": "LoE",
            "propgf_funded": "unknown",
            "substitutable": "No",
        },
    ],
}


def _contract():
    return build_contract(_FACTS, manifest_from_raw(_RAW).functions, load_kernel())


def test_sections_present_and_ordered():
    md = _contract()
    for i, header in enumerate(
        [
            "## 1. Ecosystem Alignment",
            "## 2. Public Sources",
            "## 3. Monitored Commitments",
            "## 4. Dependents and dependencies",
            "## 5. Reporting",
        ]
    ):
        assert header in md, f"missing {header}"
    # order
    idx = [md.index(h) for h in ["## 1.", "## 2.", "## 3.", "## 4.", "## 5."]]
    assert idx == sorted(idx)
    assert "## 6." not in md and "## 7." not in md


def test_repo_url_is_correct_and_present_in_s1():
    md = _contract()
    assert "filecoin-project/pgf-monitor" in md
    assert "opensource-observer" not in md


def test_placeholder_threshold_marked_to_confirm():
    md = _contract()
    s3 = md.split("## 3.")[1].split("## 4.")[0]
    # relay-liveness is a placeholder -> "(to confirm)"; beacon is not
    assert "(to confirm)" in s3
    assert s3.count("(to confirm)") == 1


def test_incident_sla_renders_under_lead_in_in_s3():
    md = _contract()
    s3 = md.split("## 3.")[1].split("## 4.")[0]
    assert "Sourced as follows:" in s3
    assert "statuspage_impact_level" in s3
    assert s3.index("Sourced as follows:") < s3.index("statuspage_impact_level")


def test_requested_additions_block_has_blank_source():
    md = _contract()
    s3 = md.split("## 3.")[1].split("## 4.")[0]
    assert "Requested additions" in s3
    assert "threshold_signers_per_round" in s3
    assert "- **Source:** \n" in s3


def test_dependency_tables_render_from_facts():
    md = _contract()
    s4 = md.split("## 4.")[1].split("## 5.")[0]
    assert "| Lotus |" in s4
    assert "| League of Entropy |" in s4


def test_reporting_has_slack_channel():
    md = _contract()
    s5 = md.split("## 5.")[1]
    assert "#filecoin-kernel updates" in s5
    assert "every two months" in s5


def test_thresholdless_function_renders_no_agreed_threshold():
    raw = {
        "team": "t",
        "maintainers": ["@m"],
        "functions": [_fn("relay-liveness", "essential", "Randomness", "relay_lag")],
    }
    del raw["functions"][0]["sla"]["threshold"]
    md = build_contract(_FACTS, manifest_from_raw(raw).functions, load_kernel())
    s3 = md.split("## 3.")[1].split("## 4.")[0]
    assert "`relay_lag` — no agreed threshold, cadence daily" in s3


def test_load_team_functions_tolerates_missing_adopted_manifest(tmp_path):
    """A draft-only team (no registry/<team>.yaml yet) still renders its staged SLAs."""
    from fpm.report.contract import load_team_functions

    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "t.yaml").write_text(
        yaml.safe_dump(
            {
                "team": "t",
                "maintainers": ["@m"],
                "x_draft": {"slate_tier": "IMP"},
                "functions": [_fn("staged", "essential", "Randomness", "staged_metric")],
            }
        )
    )
    fns = load_team_functions("t", str(tmp_path))
    assert [f.function_id for f in fns] == ["staged"]
