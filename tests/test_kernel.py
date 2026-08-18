import pytest
import yaml

from fpm.kernel import (
    KernelError,
    by_id,
    catalogued_triples,
    conformance_error,
    load_kernel,
)


def test_loads_real_inventory():
    k = load_kernel()
    assert len(k.entries) >= 20
    trips = catalogued_triples(k)
    assert ("irreplaceable", "Blockchain Core & Physical Storage", "Randomness") in trips
    assert ("essential", "UX/DX", "Explorers and Tooling") in trips
    assert ("essential", "Storage Market Middleware", "Content routing") in trips


def test_conformance_error_none_for_catalogued():
    k = load_kernel()
    assert (
        conformance_error("irreplaceable", "Blockchain Core & Physical Storage", "Randomness", k)
        is None
    )


def test_conformance_error_message_for_uncatalogued():
    k = load_kernel()
    err = conformance_error("essential", "UX/DX", "made-up-subcat", k)
    assert err is not None and "not a catalogued" in err


_LC = (
    "essential",
    "Blockchain Core & Physical Storage",
    "Ledger & Consensus",
)  # shared slot (3 fns)
_CHAIN_SYNC = "Chain sync & state management (snapshot bootstrap, heaviest-chain, RPC)"


def test_ambiguous_slot_requires_kernel_function():
    k = load_kernel()
    err = conformance_error(*_LC, k)
    assert err is not None and "maps to" in err and "kernel_function" in err


def test_kernel_function_resolves_ambiguous_slot():
    k = load_kernel()
    assert conformance_error(*_LC, k, kernel_function=_CHAIN_SYNC) is None


def test_kernel_function_in_wrong_slot_is_rejected():
    k = load_kernel()
    # a real function name, but not the one in the declared (beacon) slot
    err = conformance_error(
        "irreplaceable",
        "Blockchain Core & Physical Storage",
        "Randomness",
        k,
        kernel_function=_CHAIN_SYNC,
    )
    assert err is not None and "is in slot" in err


def test_unknown_kernel_function_is_rejected():
    k = load_kernel()
    err = conformance_error(*_LC, k, kernel_function="Not A Real Function")
    assert err is not None and "not in the kernel inventory" in err


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
