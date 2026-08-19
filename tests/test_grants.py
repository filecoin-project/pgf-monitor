"""`registry/_grants.yaml` is the bridge: Karma application <-> funded project <-> registry file.

Three sources each held a fragment of this mapping and none of them was authoritative: the
committee slate in the warehouse (app_ref + amount + an identity-resolved slug that is sometimes a
person), a `_LABEL` dict inside the dashboard notebook (app_ref -> committee-facing project name),
and `contracts/*.facts.yaml` (app_ref + money, one per team). A grant that funds two manifests, or
a project that holds two grants, could not be expressed at all.

The file is kernel-track only. A non-kernel grant gets no monitored commitments, so a row here
would imply an instrumentation gap that is not one.
"""

from __future__ import annotations

import glob
from pathlib import Path

import pytest
import yaml

from fpm.grants import GrantError, by_app_ref, by_metrics_registry, load_grants

MINIMAL = {
    "application_funding_round": "Filecoin ProPGF Batch 3",
    "application_funding_category": "Kernel",
    "application_ref_id": "APP-AAAA1111-BBBB2222",
    "application_name": "x",
    "funded_project_name": "X",
    "funded_project_oso_slug": "drand",
    "metrics_registry": "registry/randamu.yaml",
}


def test_loads_the_bridge():
    grants = load_grants()
    assert len(grants.grants) == 16, "Batch 3 funded 16 kernel grants"
    index = by_app_ref(grants)
    # APP-HDYJESMD-2WLL00, not APP-P3NAPR7O-TSQ67Q: the latter is "Curio Core + Lantern",
    # status=under_review on Karma with no approved amount, and is not FilOz. Corrected
    # 2026-08-18 against the Karma application and the signed Exhibit B.
    assert index["APP-HDYJESMD-2WLL00"].funded_project_name == "Curio (FilOz)"
    assert index["APP-HDYJESMD-2WLL00"].funded_project_oso_slug == "filozone"
    assert "APP-P3NAPR7O-TSQ67Q" not in index


def test_every_row_is_the_kernel_track():
    """A non-kernel grant has no monitored commitments, so it does not belong here at all."""
    assert {g.application_funding_category for g in load_grants().grants} == {"Kernel"}
    assert {g.application_funding_round for g in load_grants().grants} == {
        "Filecoin ProPGF Batch 3"
    }


def test_every_grant_points_at_files_that_exist():
    """The bridge is only useful if its pointers resolve: a manifest that instruments the grant and
    a facts file that carries its contract terms."""
    # contracts/ is gitignored on purpose -- the facts files carry contract terms and stay local
    # -- so a checkout without them is normal. Asserting they exist would only pass on a machine
    # that happens to hold them, and fails in CI on every checkout. metrics_registry is tracked,
    # so it is always checked.
    have_facts = any(Path("contracts").glob("*.facts.yaml"))
    missing = []
    for g in load_grants().grants:
        if not Path(g.metrics_registry).exists():
            missing.append(f"{g.application_ref_id}: metrics_registry {g.metrics_registry}")
        if have_facts and g.facts and not Path(g.facts).exists():
            missing.append(f"{g.application_ref_id}: facts {g.facts}")
    assert missing == []


def test_every_grant_is_instrumented():
    """This is the objective: every funded kernel grant names the manifest that measures it.
    `metrics_registry` is required by the schema, so this asserts the schema stays that way."""
    assert all(g.metrics_registry for g in load_grants().grants)


def test_app_refs_are_unique_and_shaped_like_karma_ids():
    refs = [g.application_ref_id for g in load_grants().grants]
    assert len(refs) == len(set(refs))
    assert all(r.startswith("APP-") for r in refs)


def test_load_rejects_a_duplicate_app_ref(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text(yaml.safe_dump({"grants": [MINIMAL, dict(MINIMAL, application_name="y")]}))
    with pytest.raises(GrantError, match="duplicate"):
        load_grants(p)


def test_load_rejects_a_non_kernel_category(tmp_path):
    """RFP-track rows are kept out by the schema, not by convention."""
    p = tmp_path / "g.yaml"
    p.write_text(yaml.safe_dump({"grants": [dict(MINIMAL, application_funding_category="RFP")]}))
    with pytest.raises(GrantError):
        load_grants(p)


def test_karma_slug_and_id_travel_together(tmp_path):
    """The slug is mutable and the id is stable, so one without the other is a half-recorded
    identity. Curio has neither, which is legal: its application never linked a Karma profile."""
    p = tmp_path / "g.yaml"
    p.write_text(
        yaml.safe_dump({"grants": [dict(MINIMAL, application_karma_project_slug="drand")]})
    )
    with pytest.raises(GrantError):
        load_grants(p)

    grants = load_grants()
    for g in grants.grants:
        assert bool(g.application_karma_project_slug) == bool(g.application_karma_project_id)


def test_the_slug_agrees_with_the_manifest_it_points_at():
    """The bridge says who is paid; the manifest's entries repeat it per metric. They must not
    disagree, or a mapping table keyed on either one tells a different story."""
    from fpm.drafts import split_draft
    from fpm.manifest import load_manifest

    problems = []
    for g in load_grants().grants:
        path = g.metrics_registry
        m = split_draft(path)[0] if "drafts/" in path else load_manifest(path)
        slugs = {fn.funded_project_oso_slug for fn in m.functions}
        if g.funded_project_oso_slug not in slugs:
            problems.append(
                f"{g.application_ref_id}: bridge says {g.funded_project_oso_slug}, "
                f"{path} says {sorted(slugs)}"
            )
    assert problems == []


def test_a_shared_manifest_is_visible_as_shared():
    """chainsafe.yaml funds Forest and Infra Services; zondax.yaml funds Core Infra and Beryx.
    That is legal, and it is exactly why each functions[] entry carries a grant_ref."""
    shared = {p: gs for p, gs in by_metrics_registry(load_grants()).items() if len(gs) > 1}
    assert set(shared) == {"registry/chainsafe.yaml", "registry/zondax.yaml"}


def test_every_facts_file_is_claimed_by_the_bridge():
    """A facts file with no grant row is a leftover from pre-award drafting, and those exist
    (js-libp2p, synaps3 were never funded). The bridge has to account for them explicitly."""
    on_disk = {p for p in glob.glob("contracts/*.facts.yaml") if "example" not in p}
    if not on_disk:
        pytest.skip("contracts/ is gitignored and absent from this checkout")
    claimed = {g.facts for g in load_grants().grants if g.facts}
    unclaimed = sorted(on_disk - claimed)
    assert unclaimed == [
        "contracts/js-libp2p.facts.yaml",
        "contracts/synaps3.facts.yaml",
    ], f"unexpected unclaimed facts files: {unclaimed}"


def _adopted_entries():
    from fpm.manifest import load_manifest

    for path in sorted(Path("registry").glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        m = load_manifest(str(path))
        for fn in m.functions:
            yield path.name, m.team, fn


def test_every_grant_ref_resolves_to_a_grant():
    """`grant_ref` is the answer to "which grant pays for this metric". A ref that resolves to
    nothing is worse than an absent one, because it reads as attributed."""
    known = set(by_app_ref(load_grants()))
    dangling = [
        f"{name}:{fn.function_id} -> {fn.grant_ref}"
        for name, _team, fn in _adopted_entries()
        if fn.grant_ref and fn.grant_ref not in known
    ]
    assert dangling == []


def test_grant_ref_agrees_with_the_payee_slug():
    """The two say related things: grant_ref names the grant, funded_project_oso_slug names who it
    pays. If they disagree, one of them is attributing money to the wrong party."""
    index = by_app_ref(load_grants())
    problems = []
    for name, _team, fn in _adopted_entries():
        if not fn.grant_ref:
            continue
        paid = index[fn.grant_ref].funded_project_oso_slug
        if paid != fn.funded_project_oso_slug:
            problems.append(
                f"{name}:{fn.function_id} pays {fn.funded_project_oso_slug} "
                f"but {fn.grant_ref} pays {paid}"
            )
    assert problems == []


def test_only_an_unfunded_entry_may_omit_its_grant_ref():
    """Every metric a grant pays for must say which grant. The one exception is the filfox
    cross-check, whose payee slug is literally `unfunded`."""
    missing = [
        f"{name}:{fn.function_id}"
        for name, _team, fn in _adopted_entries()
        if not fn.grant_ref and fn.funded_project_oso_slug != "unfunded"
    ]
    assert missing == []


def test_grant_ref_shows_which_grants_are_uninstrumented():
    """The point of the field: with a payee-slug-only bridge, a second grant on the same slug looks
    instrumented because its sibling is.

    Two grants have no adopted metric, for different reasons:
      * Beryx — both zondax.yaml entries are Core Infra's scope (archival RPC, Rosetta/Ledger).
        Beryx's own scope, chain ETL and the explorer API, is measured nowhere. Only grant_ref
        makes this visible; the payee slug `zondax` made it look covered.
      * FIL Ponto — its manifest is a draft, so nothing is adopted. Its signed §3 is empty by
        design, so that is the honest state rather than a gap to close.
    """
    attributed = {fn.grant_ref for _n, _t, fn in _adopted_entries() if fn.grant_ref}
    uninstrumented = sorted(
        g.funded_project_name
        for g in load_grants().grants
        if g.application_ref_id not in attributed
    )
    assert uninstrumented == ["Beryx", "FIL Ponto"], f"changed: {uninstrumented}"
