"""The PR gate and the live dry-run over an `oso-sql` function.

The property under test is the one that makes the kind safe to have at all: the table allowlist is
supplied by the CALLER from the base ref, so a PR cannot both allowlist a table and read it. Both
gates must therefore refuse a table they were not given — and refuse it BEFORE any query runs.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fpm.manifest import FunctionSpec, Manifest, SlaSpec, SourceSpec
from fpm.oso.client import FakeOsoClient
from scripts.dry_run_pr import dry_run
from scripts.validate_pr import validate_manifest

AS_OF = datetime(2026, 9, 10, tzinfo=timezone.utc)
ALLOWED = {"filecoin.data_portal.filecoin_pay_rails"}
PRIVATE = "filecoin.funding_model_static.applicant_identity"


def _manifest(sql: str) -> Manifest:
    return Manifest(
        team="filoz",
        maintainers=["@someone"],
        functions=[
            FunctionSpec(
                function_id="curio-filecoin-pay-fwss-volume",
                kernel_id="dealmaking-pdp-retrieval",
                tier="essential",
                category="Blockchain Core & Physical Storage",
                sub_category="Block Production (mining)",
                sla=SlaSpec(
                    statement="Filecoin Pay volume across FWSS operators, measured daily",
                    metric="filecoin_pay_volume_fwss_usd",
                    unscored_reason="no-signed-bar",
                    cadence="daily",
                ),
                source=SourceSpec(adapter="oso-sql", kind="oso-sql", sql=sql),
            )
        ],
    )


GOOD = _manifest("SELECT COUNT(*) FROM filecoin.data_portal.filecoin_pay_rails")
PRIVATE_READ = _manifest(f"SELECT COUNT(*) FROM {PRIVATE}")


def test_gate_accepts_an_allowlisted_table():
    ok, md = validate_manifest(None, GOOD, set(), AS_OF, ALLOWED)
    assert ok, md


def test_gate_needs_no_egress_host_for_oso_sql():
    """An empty HOST allowlist must not fail an oso-sql entry — nothing is fetched."""
    ok, _ = validate_manifest(None, GOOD, set(), AS_OF, ALLOWED)
    assert ok


def test_gate_rejects_a_private_table():
    ok, md = validate_manifest(None, PRIVATE_READ, set(), AS_OF, ALLOWED)
    assert not ok
    assert "warehouse SQL rejected" in md and "applicant_identity" in md


def test_gate_fails_closed_when_given_no_table_allowlist():
    """A base ref predating _sql_allowlist.txt yields an empty set, which must refuse, not allow."""
    ok, md = validate_manifest(None, GOOD, set(), AS_OF, None)
    assert not ok
    assert "not on the warehouse allowlist" in md


def test_dry_run_measures_an_oso_sql_function_without_provisioning():
    client = FakeOsoClient(query_rows=[{"_col0": 18801.89}])
    ok, md = dry_run(
        GOOD,
        {"curio-filecoin-pay-fwss-volume"},
        client,
        "org",
        set(),
        AS_OF,
        sql_allowlist=ALLOWED,
    )
    assert ok, md
    assert "observed 18801.89" in md
    # The whole point: no throwaway dataset to create, and so none to leak or delete.
    assert client._datasets == {}


def test_dry_run_fails_closed_without_a_table_allowlist():
    client = FakeOsoClient(query_rows=[{"_col0": 1.0}])
    ok, md = dry_run(
        GOOD, {"curio-filecoin-pay-fwss-volume"}, client, "org", set(), AS_OF, sql_allowlist=None
    )
    assert not ok
    assert "not on the warehouse allowlist" in md


def test_dry_run_refuses_a_private_table_before_querying():
    class Tripwire(FakeOsoClient):
        def query(self, sql):  # pragma: no cover - must never be reached
            raise AssertionError(f"a query was sent for a refused table: {sql}")

    ok, md = dry_run(
        PRIVATE_READ,
        {"curio-filecoin-pay-fwss-volume"},
        Tripwire(),
        "org",
        set(),
        AS_OF,
        sql_allowlist=ALLOWED,
    )
    assert not ok
    assert "applicant_identity" in md
