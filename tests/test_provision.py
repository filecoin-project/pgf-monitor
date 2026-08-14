from datetime import datetime, timezone

import pytest

from fpm.domain import window_for
from fpm.manifest import load_manifest
from fpm.provision import (
    config_shape_fingerprint,
    missing_secret,
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


def test_auth_resolves_the_secret_from_the_environment(monkeypatch):
    """OSO wants the VALUE, not a ref name: it lifts the value into its own store and keeps a
    path-derived marker. Sending the name makes it authenticate as the literal string."""
    monkeypatch.setenv("GH_API_TOKEN", "s3cret-value")
    fn = _fn()
    fn.source.auth_secret_ref = "GH_API_TOKEN"
    config = build_ingestion_config(fn, window_for(fn.sla.cadence, AS_OF), "chainsafe")
    assert config["client"]["auth"] == {
        "type": "bearer",
        "token": {"$type": "secret", "value": "s3cret-value"},
    }


def test_shape_is_identical_with_and_without_the_credential(monkeypatch):
    """This is what lets the scheduled job run WITHOUT the token: OSO keeps the credential after
    attach, so a runner that only compares config shape must reach the same fingerprint as the
    host that provisioned. If these ever diverge, every authenticated dataset is recreated nightly
    — and the runner cannot recreate one, so every such metric goes blank."""
    fn = _fn()
    fn.source.auth_secret_ref = "GH_API_TOKEN"
    monkeypatch.setenv("GH_API_TOKEN", "s3cret-value")
    with_secret = build_ingestion_config(fn, window_for(fn.sla.cadence, AS_OF), "chainsafe")
    monkeypatch.delenv("GH_API_TOKEN")
    without = build_ingestion_config(fn, window_for(fn.sla.cadence, AS_OF), "chainsafe")
    assert config_shape_fingerprint(with_secret) == config_shape_fingerprint(without)
    assert "value" not in without["client"]["auth"]["token"]  # never attach a value-less secret


def test_missing_secret_is_named(monkeypatch):
    monkeypatch.delenv("GH_API_TOKEN", raising=False)
    fn = _fn()
    fn.source.auth_secret_ref = "GH_API_TOKEN"
    assert missing_secret(fn) == "GH_API_TOKEN"
    monkeypatch.setenv("GH_API_TOKEN", "x")
    assert missing_secret(fn) is None


def test_no_auth_block_when_none_declared():
    assert (
        "auth"
        not in build_ingestion_config(_fn(), window_for("daily", AS_OF), "chainsafe")["client"]
    )


def test_config_declares_the_paginator():
    """dlt auto-detects a paginator when none is given: GitHub's Link headers then make a
    `commits?per_page=30` fetch walk the entire history, exhausting the unauthenticated
    60 req/hour budget on one metric and failing every later GitHub metric with a 403."""
    fn = _fn()
    config = build_ingestion_config(fn, window_for(fn.sla.cadence, AS_OF), "chainsafe")
    assert config["resources"][0]["endpoint"]["paginator"] == "single_page"


def test_config_honors_a_declared_paginator():
    fn = _fn()
    fn.source.paginator = "header_link"
    config = build_ingestion_config(fn, window_for(fn.sla.cadence, AS_OF), "chainsafe")
    assert config["resources"][0]["endpoint"]["paginator"] == "header_link"
