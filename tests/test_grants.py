"""`registry/_grants.yaml` is the bridge: Karma app id <-> OSO project slug <-> registry file.

Three sources each held a fragment of this mapping and none of them was authoritative: the
committee slate in the warehouse (app_ref + amount + an identity-resolved slug that is sometimes a
person), a `_LABEL` dict inside the dashboard notebook (app_ref -> committee-facing project name),
and `contracts/*.facts.yaml` (app_ref + money, one per team). A grant that funds two manifests, or
a project that holds two grants, could not be expressed at all.
"""

from __future__ import annotations

import glob
from pathlib import Path

import pytest
import yaml

from fpm.grants import GrantError, by_app_ref, load_grants


def test_loads_the_bridge():
    grants = load_grants()
    assert len(grants.grants) >= 16
    index = by_app_ref(grants)
    assert index["APP-P3NAPR7O-TSQ67Q"].label == "Curio (FilOz)"
    assert index["APP-P3NAPR7O-TSQ67Q"].funded_project_oso_slug == "filozone"


def test_every_grant_points_at_files_that_exist():
    """The bridge is only useful if its pointers resolve: a manifest that instruments the grant and
    a facts file that carries its contract terms."""
    # contracts/ is gitignored on purpose -- the facts files carry contract terms and stay local
    # -- so a checkout that has none is normal, and asserting they exist would only pass on a
    # machine that happens to hold them. Check the facts pointers only when the directory is
    # populated; the manifest pointers are tracked and always checked.
    have_facts = any(Path("contracts").glob("*.facts.yaml"))
    missing = []
    for g in load_grants().grants:
        if g.manifest and not Path(g.manifest).exists():
            missing.append(f"{g.app_ref}: manifest {g.manifest}")
        if have_facts and g.facts and not Path(g.facts).exists():
            missing.append(f"{g.app_ref}: facts {g.facts}")
    assert missing == []


def test_app_refs_are_unique_and_shaped_like_karma_ids():
    refs = [g.app_ref for g in load_grants().grants]
    assert len(refs) == len(set(refs))
    assert all(r.startswith("APP-") for r in refs)


def test_load_rejects_a_duplicate_app_ref(tmp_path):
    row = {
        "app_ref": "APP-AAAA1111-BBBB2222",
        "label": "x",
        "funded_project_oso_slug": "drand",
        "status": "funded",
    }
    p = tmp_path / "g.yaml"
    p.write_text(yaml.safe_dump({"grants": [row, dict(row, label="y")]}))
    with pytest.raises(GrantError, match="duplicate"):
        load_grants(p)


def test_a_funded_grant_names_the_manifest_that_instruments_it():
    """This is the objective: every funded kernel grant is instrumented in this repo. A funded
    grant with no manifest is the gap list, and it must be visible rather than implied."""
    uninstrumented = [
        g.app_ref for g in load_grants().grants if g.status == "funded" and not g.manifest
    ]
    assert uninstrumented == [], f"funded grants with no manifest: {uninstrumented}"


def test_the_slug_agrees_with_the_manifest_it_points_at():
    """The bridge says who is paid; the manifest's entries repeat it per metric. They must not
    disagree, or a mapping table keyed on either one tells a different story."""
    from fpm.drafts import split_draft
    from fpm.manifest import load_manifest

    problems = []
    for g in load_grants().grants:
        if not g.manifest:
            continue
        m = split_draft(g.manifest)[0] if "drafts/" in g.manifest else load_manifest(g.manifest)
        slugs = {fn.funded_project_oso_slug for fn in m.functions}
        if g.funded_project_oso_slug not in slugs:
            problems.append(
                f"{g.app_ref}: bridge says {g.funded_project_oso_slug}, {g.manifest} says {sorted(slugs)}"
            )
    assert problems == []


def test_every_facts_file_is_claimed_by_the_bridge():
    """A facts file with no grant row is a leftover from pre-award drafting, and those exist
    (js-libp2p, synaps3 were never funded). The bridge has to account for them explicitly."""
    on_disk = {p for p in glob.glob("contracts/*.facts.yaml") if "example" not in p}
    if not on_disk:
        pytest.skip("contracts/ is gitignored and absent from this checkout")
    claimed = {g.facts for g in load_grants().grants if g.facts}
    unclaimed = sorted(on_disk - claimed)
    assert unclaimed == [], f"facts files no grant row claims: {unclaimed}"
