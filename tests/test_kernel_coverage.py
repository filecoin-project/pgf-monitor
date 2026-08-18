"""The registry is the source of truth for kernel coverage; every published number is derived.

These tests hold two things: the identity rule (a metric counts for the ONE kernel function it
names, not for every function sharing its slot) and the derivation (docs/kernel-coverage.md,
badges.json and the dashboard's embedded payload are exactly what the generator produces from
the current registry — so they cannot drift).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from fpm.kernel import load_kernel
from fpm.manifest import FunctionSpec, SlaSpec, SourceSpec
from fpm.kernel import NON_KERNEL_ID
from scripts.kernel_coverage import (
    BADGES_JSON,
    DASHBOARD,
    EMBED_END,
    EMBED_START,
    OUT,
    badges_data,
    collect,
    counts,
    coverage_json,
    render,
    resolve_kernel_id,
)


def _fn(kernel_id="", tier="irreplaceable", category="", sub_category=""):
    return FunctionSpec(
        function_id="probe",
        kernel_id=kernel_id,
        tier=tier,
        category=category,
        sub_category=sub_category,
        sla=SlaSpec(statement="s", metric="m", cadence="daily"),
        source=SourceSpec(adapter="oso", kind="http-json", base_url="https://api.llama.fi"),
    )


def _ids():
    return {e.id for e in load_kernel().entries}


def test_a_known_id_resolves_to_itself():
    assert resolve_kernel_id(_fn(kernel_id="chain-sync-state"), _ids()) == (
        "chain-sync-state",
        None,
    )


def test_an_unknown_id_is_reported_not_guessed():
    name, why = resolve_kernel_id(_fn(kernel_id="not-a-real-id"), _ids())
    assert name is None and "not in the kernel inventory" in why


def test_an_unset_id_is_reported():
    name, why = resolve_kernel_id(_fn(), _ids())
    assert name is None and "unset" in why


def test_non_kernel_resolves_to_nothing_without_being_an_error():
    """The metric is real; it is simply not evidence for a catalogued kernel function, so it must
    inflate no coverage number and must not read as a mistake."""
    assert resolve_kernel_id(_fn(kernel_id=NON_KERNEL_ID), _ids()) == (None, None)


def test_every_registry_entry_resolves_to_one_kernel_id():
    _, _, unresolved = collect()
    assert unresolved == []


def test_the_payload_is_keyed_by_kernel_id():
    payload = coverage_json()
    by_id = {f["id"]: f for f in payload["functions"]}
    assert len(by_id) == len(payload["functions"])
    ankr = {e["function_id"] for e in by_id["chain-sync-state"]["entries"] if e["team"] == "ankr"}
    assert "chain-sync-rpc-mainnet-head-lag" in ankr
    assert "ankr" not in {e["team"] for e in by_id["forest-full-node"]["entries"]}


def _a_shared_slot():
    """A (tier, category, sub_category) slot several kernel functions live in, plus their ids.

    Shared slots are what made the old triple-keyed join wrong, and they are still where a draft
    can propose moving a metric from one kernel function to a sibling without changing anything
    else about it.
    """
    by_slot: dict[tuple[str, str, str], list[str]] = {}
    for e in load_kernel().entries:
        by_slot.setdefault((e.tier, e.category, e.sub_category), []).append(e.id)
    for slot, ids in by_slot.items():
        if len(ids) > 1:
            return slot, ids
    pytest.skip("no shared slot in the kernel inventory")


def test_an_adopted_metric_is_never_reported_as_a_draft():
    """A draft is how a team proposes its NEXT version; it must not overwrite what is adopted
    today. ankr had two live, passing metrics published as `draft` because both files were
    written into one dict keyed by slot."""
    entries, _, _ = collect()
    adopted = {
        (e["team"], e["function_id"], e["metric"])
        for items in entries.values()
        for e in items
        if e["state"] == "adopted"
    }
    drafted = {
        (e["team"], e["function_id"], e["metric"])
        for items in entries.values()
        for e in items
        if e["state"] == "draft"
    }
    assert adopted & drafted == set()


def test_a_shadowed_adopted_entry_is_flagged_as_having_a_pending_draft():
    entries, _, _ = collect()
    flagged = [
        e for items in entries.values() for e in items if e.get("pending_draft") and e["state"]
    ]
    assert all(e["state"] == "adopted" for e in flagged)


def test_adopted_coverage_never_exceeds_modelled_coverage():
    c = counts(collect()[0], load_kernel())
    assert c["live"] <= c["adopted"] <= c["with_drafts"] <= c["functions"]


def test_committed_coverage_doc_matches_the_registry():
    assert OUT.read_text() == render(), (
        "docs/kernel-coverage.md is stale — regenerate: "
        "uv run python scripts/kernel_coverage.py --write"
    )


def test_committed_badges_match_the_registry():
    assert json.loads(BADGES_JSON.read_text()) == badges_data(), (
        "badges.json is stale — regenerate: uv run python scripts/kernel_coverage.py --badges"
    )


def test_embedded_dashboard_payload_matches_the_registry():
    text = DASHBOARD.read_text()
    body = text[text.index(EMBED_START) + len(EMBED_START) : text.index(EMBED_END)]
    literal = body[body.index("'") : body.rindex("'") + 1]
    assert json.loads(ast.literal_eval(literal)) == coverage_json(), (
        "the dashboard's COVERAGE literal is stale — regenerate: "
        "uv run python scripts/kernel_coverage.py --embed"
    )


def test_the_generator_is_the_only_writer_of_the_derived_artifacts():
    """A reminder in the artifacts themselves, so a hand-edit looks wrong to a reader too."""
    assert "do not edit by hand" in OUT.read_text()
    assert "regenerate it with" in Path("README.md").read_text()


def _manifest_yaml(kernel_id: str, slot, metric="probe_metric") -> str:
    import yaml

    return yaml.safe_dump(
        {
            "team": "probeteam",
            "maintainers": ["@someone"],
            "functions": [
                {
                    "function_id": "probe-fn",
                    "kernel_id": kernel_id,
                    "funded_project_oso_slug": "drand",
                    "origin": "oso",
                    "tier": slot[0],
                    "category": slot[1],
                    "sub_category": slot[2],
                    "sla": {
                        "statement": "a probe",
                        "metric": metric,
                        "threshold": {"op": "<=", "value": 1},
                        "cadence": "daily",
                    },
                    "source": {
                        "adapter": "oso",
                        "kind": "http-json",
                        "base_url": "https://api.llama.fi",
                        "query": "/v2/x",
                        "extract": {"column": "v", "reduce": "single"},
                    },
                }
            ],
        },
        sort_keys=False,
    )


def test_a_draft_that_moves_a_metric_to_another_kernel_id_keeps_both(tmp_path):
    """A draft may PROPOSE reassigning a metric to a different kernel function. Deduping on
    (team, function_id, metric) alone treated that as a pending update to the adopted entry, so
    the proposed function got no draft coverage at all and the move was invisible."""
    slot, names = _a_shared_slot()
    adopted_fn, proposed_fn = names[0], names[1]
    registry = tmp_path / "registry"
    drafts = registry / "drafts"
    drafts.mkdir(parents=True)
    (registry / "probeteam.yaml").write_text(_manifest_yaml(adopted_fn, slot))
    (drafts / "probeteam.yaml").write_text(_manifest_yaml(proposed_fn, slot))

    entries, _, unresolved = collect(registry_dir=registry)

    assert unresolved == []
    adopted = [e for e in entries.get(adopted_fn, []) if e["team"] == "probeteam"]
    proposed = [e for e in entries.get(proposed_fn, []) if e["team"] == "probeteam"]
    assert [e["state"] for e in adopted] == ["adopted"], "the adopted assignment must survive"
    assert [e["state"] for e in proposed] == ["draft"], "the proposed reassignment must be visible"
    assert adopted[0]["pending_draft"] is True


def test_a_draft_identical_to_the_adopted_entry_is_only_a_pending_flag(tmp_path):
    slot, names = _a_shared_slot()
    registry = tmp_path / "registry"
    drafts = registry / "drafts"
    drafts.mkdir(parents=True)
    (registry / "probeteam.yaml").write_text(_manifest_yaml(names[0], slot))
    (drafts / "probeteam.yaml").write_text(_manifest_yaml(names[0], slot))

    entries, _, _ = collect(registry_dir=registry)

    mine = [e for e in entries.get(names[0], []) if e["team"] == "probeteam"]
    assert len(mine) == 1
    assert mine[0]["state"] == "adopted" and mine[0]["pending_draft"] is True


def test_kernel_ids_do_not_collide_with_sla_ids_or_team_names():
    """Kernel ids are immutable; an SLA `function_id` is part of the primary key of every row in
    observations.csv and thresholds.csv. When the two namespaces collide the SLA side has to move,
    which is the expensive direction, so keep them disjoint from the start."""
    import glob

    import yaml

    kernel_ids = {e.id for e in load_kernel().entries}
    teams, fids = set(), set()
    for scope in ("registry/*.yaml", "registry/drafts/*.yaml"):
        for path in sorted(glob.glob(scope)):
            if Path(path).name.startswith("_"):
                continue
            raw = yaml.safe_load(Path(path).read_text())
            teams.add(raw["team"])
            fids |= {f["function_id"] for f in raw["functions"]}
    assert kernel_ids & fids == set(), "a kernel id doubles as an SLA function_id"
    assert kernel_ids & teams == set(), "a kernel id doubles as a team name"


def test_every_entry_declares_who_is_funded():
    """`funded_project_oso_slug` is required, and `unfunded` is the explicit way to say nobody is
    paid for this kernel function yet."""
    entries, _, _ = collect()
    slugs = {e["funded_project"] for items in entries.values() for e in items}
    assert "" not in slugs and None not in slugs


def test_a_source_that_fetches_a_repo_enumerates_it():
    """15 metrics read a GitHub repository directly. If the URL and the enumeration disagree, one
    of them is wrong about what is being measured."""
    import glob

    from fpm.drafts import split_draft
    from fpm.governance.repos import source_repo_error
    from fpm.manifest import load_manifest

    problems = []
    for scope, is_draft in (("registry/*.yaml", False), ("registry/drafts/*.yaml", True)):
        for path in sorted(glob.glob(scope)):
            if Path(path).name.startswith("_"):
                continue
            m = split_draft(path)[0] if is_draft else load_manifest(path)
            for fn in m.functions:
                err = source_repo_error(fn)
                if err:
                    problems.append(f"{m.team}/{fn.function_id}: {err}")
    assert problems == []
