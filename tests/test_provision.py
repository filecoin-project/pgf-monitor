from datetime import datetime, timezone

import pytest

from fpm.domain import window_for
from fpm.manifest import load_manifest
from fpm.provision import (
    EgressError,
    assert_egress_allowed,
    build_ingestion_config,
    config_fingerprint,
    dataset_name,
    resource_name,
)

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _fn():
    return load_manifest("tests/fixtures/chainsafe_oso.yaml").functions[0]


def test_names_are_deterministic_and_safe():
    assert dataset_name("chainsafe", "filecoin-tvl") == dataset_name("chainsafe", "filecoin-tvl")
    assert "-" not in dataset_name("chainsafe", "filecoin-tvl")
    assert resource_name("chainsafe", "filecoin-tvl").startswith("fpm_")


def test_build_config_shape():
    fn = _fn()
    cfg = build_ingestion_config(fn, window_for(fn.sla.cadence, AS_OF), "chainsafe")
    assert cfg["client"]["base_url"] == "https://api.llama.fi"
    res = cfg["resources"][0]
    assert res["write_disposition"] == "replace"
    assert res["endpoint"]["path"] == "/v2/historicalChainTvl/Filecoin"
    assert "data_selector" not in res["endpoint"]  # path == "$" -> top-level array


def test_max_table_nesting_passed_when_set():
    # max_table_nesting is passed through to the resource when a function declares it.
    m = load_manifest("tests/fixtures/kernel_demo.yaml")
    explorer = next(f for f in m.functions if f.function_id == "mainnet-block-explorer")
    explorer = explorer.model_copy(deep=True)
    explorer.source.max_table_nesting = 2
    cfg = build_ingestion_config(explorer, window_for(explorer.sla.cadence, AS_OF), "kernel-demo")
    assert cfg["resources"][0]["max_table_nesting"] == 2
    # a function with no nesting cap -> key absent
    drand = next(f for f in m.functions if f.function_id == "randomness-beacon")
    cfg2 = build_ingestion_config(drand, window_for(drand.sla.cadence, AS_OF), "kernel-demo")
    assert "max_table_nesting" not in cfg2["resources"][0]


def test_egress_allows_declared_host():
    fn = _fn()
    assert_egress_allowed(fn, {"api.llama.fi"})  # no raise


def test_egress_refuses_unlisted_host():
    fn = _fn()
    with pytest.raises(EgressError):
        assert_egress_allowed(fn, {"example.com"})


def test_fingerprint_stable_and_window_sensitive():
    fn = _fn()
    w1 = window_for(fn.sla.cadence, AS_OF)
    assert config_fingerprint(fn, w1) == config_fingerprint(fn, w1)
    w2 = window_for(fn.sla.cadence, datetime(2026, 6, 1, tzinfo=timezone.utc))
    assert config_fingerprint(fn, w1) != config_fingerprint(fn, w2)


def test_post_params_become_json_body():
    # dlt's rest_api sends `params` as URL query params; a JSON-RPC POST needs the
    # payload in `json`. Found live 2026-07-15: Filecoin.ChainHead arrived as
    # ?id=1&method=... -> 400. POST params must translate to a request body.
    fn = _fn()
    fn = fn.model_copy(
        update={
            "source": fn.source.model_copy(
                update={
                    "method": "POST",
                    "params": {"jsonrpc": "2.0", "method": "Filecoin.ChainHead", "id": 1},
                }
            )
        }
    )
    cfg = build_ingestion_config(fn, window_for(fn.sla.cadence, AS_OF), "t")
    ep = cfg["resources"][0]["endpoint"]
    assert ep["method"] == "POST"
    assert ep["json"] == {"jsonrpc": "2.0", "method": "Filecoin.ChainHead", "id": 1}
    assert "params" not in ep
