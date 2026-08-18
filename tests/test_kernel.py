import pytest
import yaml

from fpm.kernel import (
    KernelError,
    by_id,
    catalogued_triples,
    conformance_error,
    load_kernel,
)


#: a real slot: (tier, category, sub_category) of chain-sync-state
_LC = ("essential", "Blockchain Core & Physical Storage", "Ledger & Consensus")


def test_loads_real_inventory():
    k = load_kernel()
    assert len(k.entries) >= 20
    trips = catalogued_triples(k)
    assert ("irreplaceable", "Blockchain Core & Physical Storage", "Randomness") in trips
    assert ("essential", "UX/DX", "Explorers and Tooling") in trips
    assert ("essential", "Storage Market Middleware", "Content routing") in trips


def test_bad_category_raises(tmp_path):
    bad = tmp_path / "k.yaml"
    bad.write_text(
        "entries:\n  - tier: essential\n    category: Not A Category\n"
        "    sub_category: X\n    function: f\n"
    )
    with pytest.raises(KernelError):
        load_kernel(bad)


def test_missing_function_raises(tmp_path):
    bad = tmp_path / "k.yaml"
    bad.write_text("entries:\n  - tier: essential\n    category: 'UX/DX'\n    sub_category: X\n")
    with pytest.raises(KernelError):
        load_kernel(bad)


#: The slugs as minted by Plan 9. Ids are the join key and are immutable once adopted, so this
#: is a superset assertion: adding a 30th kernel function needs no test edit, but changing or
#: removing one of these fails loudly.
FROZEN_KERNEL_IDS = frozenset(
    {
        "fvm-execution-engine",
        "builtin-actor-suite",
        "proving-subsystem",
        "p2p-networking-stack",
        "distributed-randomness-beacon",
        "consensus-validation-client",
        "chain-sync-state",
        "forest-full-node",
        "block-production",
        "sealing-pipeline",
        "proving-scheduler",
        "venus-pooled-mining",
        "evm-eam-actors",
        "randomness-relays",
        "validated-snapshots",
        "bootstrap-seed-nodes",
        "groth16-params",
        "calibnet-upgrade-rehearsal",
        "infra-stewardship",
        "calibnet-miners",
        "calibnet-explorer",
        "network-monitoring-ir",
        "open-network-datasets",
        "chain-etl-spacescope",
        "chain-etl-indexing",
        "mainnet-explorer",
        "network-documentation",
        "content-routing-ads",
        "dealmaking-pdp-retrieval",
    }
)


def test_every_entry_has_a_unique_id():
    k = load_kernel()
    ids = [e.id for e in k.entries]
    assert all(ids), "every kernel entry needs an id"
    assert len(ids) == len(set(ids))
    assert "chain-sync-state" in ids
    assert "forest-full-node" in ids


def test_kernel_ids_are_frozen():
    """A rename is a new id plus a migration, never an edit in place: the slug is the join key
    that manifests, coverage and (soon) the warehouse mapping all point at."""
    assert {e.id for e in load_kernel().entries} >= FROZEN_KERNEL_IDS


def test_by_id_indexes_the_inventory():
    k = load_kernel()
    index = by_id(k)
    assert len(index) == len(k.entries)
    assert index["chain-sync-state"].sub_category == "Ledger & Consensus"


def test_load_rejects_a_duplicate_id(tmp_path):
    entry = {
        "tier": "essential",
        "category": "UX/DX",
        "sub_category": "Explorers and Tooling",
        "function": "A",
        "value": "",
    }
    raw = {"entries": [{**entry, "id": "dup"}, {**entry, "id": "dup", "function": "B"}]}
    p = tmp_path / "k.yaml"
    p.write_text(yaml.safe_dump(raw))
    with pytest.raises(KernelError, match="duplicate"):
        load_kernel(p)


def test_load_rejects_a_missing_id(tmp_path):
    raw = {
        "entries": [
            {
                "tier": "essential",
                "category": "UX/DX",
                "sub_category": "Explorers and Tooling",
                "function": "A",
                "value": "",
            }
        ]
    }
    p = tmp_path / "k.yaml"
    p.write_text(yaml.safe_dump(raw))
    with pytest.raises(KernelError):
        load_kernel(p)


# --- id-first conformance. The prose display name is never matched: it is presentation text.

NON_KERNEL = "non-kernel"


def test_conformance_accepts_a_matching_kernel_id():
    assert conformance_error(*_LC, load_kernel(), kernel_id="chain-sync-state") is None


def test_conformance_rejects_an_unknown_kernel_id():
    err = conformance_error(*_LC, load_kernel(), kernel_id="not-a-real-id")
    assert err and "not-a-real-id" in err


def test_conformance_rejects_a_kernel_id_from_another_slot():
    err = conformance_error(
        "essential", "UX/DX", "Explorers and Tooling", load_kernel(), kernel_id="chain-sync-state"
    )
    assert err and "chain-sync-state" in err and "Ledger & Consensus" in err


def test_conformance_accepts_non_kernel_and_skips_the_slot_check():
    """A metric that evidences no catalogued kernel function says so explicitly, the same way an
    omitted threshold says 'measured, not scored'."""
    assert conformance_error(*_LC, load_kernel(), kernel_id=NON_KERNEL) is None
    assert (
        conformance_error("essential", "UX/DX", "made-up", load_kernel(), kernel_id=NON_KERNEL)
        is None
    )


def test_non_kernel_is_not_an_inventory_id():
    assert NON_KERNEL not in {e.id for e in load_kernel().entries}


def test_conformance_requires_a_kernel_id():
    err = conformance_error(*_LC, load_kernel())
    assert err and "kernel_id is required" in err


def test_conformance_error_names_the_slot_when_the_id_is_elsewhere():
    err = conformance_error(
        "essential", "UX/DX", "Explorers and Tooling", load_kernel(), kernel_id="chain-sync-state"
    )
    assert err and "Ledger & Consensus" in err


def test_an_uncatalogued_slot_is_caught_through_its_id():
    """The slot is still checked, but against the inventory row the id names."""
    err = conformance_error(
        "essential", "UX/DX", "made-up-subcat", load_kernel(), kernel_id="chain-sync-state"
    )
    assert err and "made-up-subcat" in err
