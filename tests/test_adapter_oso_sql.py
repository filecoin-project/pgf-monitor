"""OsoSqlAdapter: a reading taken straight from the warehouse, with no ingestion in the way.

The point of the kind is that none of the provisioning machinery runs — no dataset is created, no
run is triggered, no egress host is contacted. These tests assert that absence as much as the
value, because a warehouse read that quietly provisioned something would carry all the failure
modes it exists to avoid.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fpm.adapters.oso_sql import OsoSqlAdapter
from fpm.adapters.registry import build_adapters
from fpm.domain import window_for
from fpm.evaluate import evaluate_sla
from fpm.manifest import load_manifest
from fpm.oso.client import FakeOsoClient

AS_OF = datetime(2026, 9, 10, tzinfo=timezone.utc)
ALLOWED = {
    "filecoin.data_portal.daily_filecoin_pay_operators_metrics",
    "filecoin.data_portal.filecoin_pay_rails",
}


def _fn():
    return load_manifest("tests/fixtures/filoz_oso_sql.yaml").functions[0]


def _fetch(client, allowed=ALLOWED):
    fn = _fn()
    adapter = OsoSqlAdapter(client, allowed_tables=allowed)
    return fn, adapter.fetch(fn, "filoz", window_for(fn.sla.cadence, AS_OF))


def test_single_scalar_becomes_the_reading_value():
    client = FakeOsoClient(query_rows=[{"_col0": 18801.890343191357}])
    fn, reading = _fetch(client)
    assert reading.claim.value == 18801.890343191357
    assert reading.claim.origin == "independent"
    assert reading.adapter == "oso-sql"
    assert reading.source_metadata == {"kind": "oso-sql"}
    # No bar is agreed, so a good reading is "unscored", not "pass".
    assert evaluate_sla(reading, fn, "filoz").outcome == "unscored"


def test_nothing_is_provisioned_and_no_run_is_triggered():
    client = FakeOsoClient(query_rows=[{"_col0": 1.0}])
    _fetch(client)
    assert client._datasets == {}
    assert client._runs == {}
    assert client._configs == {}


def test_evidence_carries_no_run_ref_but_still_hashes_the_payload():
    client = FakeOsoClient(query_rows=[{"_col0": 1.0}])
    _, reading = _fetch(client)
    ev = reading.claim.evidence
    assert ev is not None
    assert ev.oso_run_ref is None  # there is no ingestion run to point at
    assert ev.raw_payload_hash is None
    assert ev.canonical_payload_hash and ev.request_fingerprint and ev.evidence_bundle_hash


def test_request_fingerprint_is_stable_across_runs_of_the_same_day():
    """It must key off the DECLARED sql and window, never the bound timestamps."""
    a = _fetch(FakeOsoClient(query_rows=[{"_col0": 1.0}]))[1]
    b = _fetch(FakeOsoClient(query_rows=[{"_col0": 2.0}]))[1]
    assert a.claim.evidence.request_fingerprint == b.claim.evidence.request_fingerprint


def test_a_table_off_the_allowlist_is_indeterminate_not_a_crash():
    fn, reading = _fetch(FakeOsoClient(query_rows=[{"_col0": 1.0}]), allowed=set())
    assert reading.claim.value is None
    assert "not on the warehouse allowlist" in reading.source_metadata["sql_error"]
    assert evaluate_sla(reading, fn, "filoz").outcome == "indeterminate"


def test_a_query_error_is_indeterminate():
    class Boom(FakeOsoClient):
        def query(self, sql):
            raise RuntimeError("trino exploded")

    fn, reading = _fetch(Boom())
    assert reading.claim.value is None
    assert "trino exploded" in reading.source_metadata["sql_error"]
    assert evaluate_sla(reading, fn, "filoz").outcome == "indeterminate"


def test_more_than_one_row_is_indeterminate():
    fn, reading = _fetch(FakeOsoClient(query_rows=[{"_col0": 1.0}, {"_col0": 2.0}]))
    assert reading.claim.value is None
    assert "expected 1" in reading.source_metadata["sql_error"]


def test_a_null_result_is_indeterminate_rather_than_zero():
    """SUM over no matching rows returns NULL; recording it as 0.0 would invent a fact."""
    fn, reading = _fetch(FakeOsoClient(query_rows=[{"_col0": None}]))
    assert reading.claim.value is None
    assert "single non-null cell" in reading.source_metadata["sql_error"]


def test_a_non_numeric_result_is_indeterminate():
    fn, reading = _fetch(FakeOsoClient(query_rows=[{"_col0": "FWSS"}]))
    assert reading.claim.value is None
    assert "not numeric" in reading.source_metadata["sql_error"]


def test_the_registry_exposes_the_adapter_under_its_manifest_name():
    adapters = build_adapters(
        __import__("pathlib").Path("tests/fixtures"),
        oso_client=FakeOsoClient(),
        org_id="org",
        sql_allowlist=ALLOWED,
    )
    assert adapters["oso-sql"].name == "oso-sql"


def test_the_registry_defaults_to_an_empty_table_allowlist():
    """Omitting the committee list must refuse every table, not accept every table."""
    adapters = build_adapters(
        __import__("pathlib").Path("tests/fixtures"),
        oso_client=FakeOsoClient(query_rows=[{"_col0": 1.0}]),
        org_id="org",
    )
    fn = _fn()
    reading = adapters["oso-sql"].fetch(fn, "filoz", window_for(fn.sla.cadence, AS_OF))
    assert reading.claim.value is None
    assert "not on the warehouse allowlist" in reading.source_metadata["sql_error"]
