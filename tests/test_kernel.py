import pytest

from fpm.kernel import KernelError, catalogued_triples, conformance_error, load_kernel


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
