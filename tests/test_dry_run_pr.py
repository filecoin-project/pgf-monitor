from datetime import datetime, timezone

from fpm.manifest import load_manifest
from fpm.oso.client import FakeOsoClient
from scripts.dry_run_pr import changed_function_ids, dry_run

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
ALLOW = {"api.llama.fi", "api.drand.sh", "filfox.info"}


def test_changed_ids_detects_modified_and_added():
    base = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    head = base.model_copy(deep=True)
    head.functions[0].sla.threshold_value = 2.0
    assert base.functions[0].function_id in changed_function_ids(base, head)


def test_dry_run_success_reads_back_and_cleans_up():
    head = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    changed = {head.functions[0].function_id}
    client = FakeOsoClient(
        run_status="SUCCESS", query_rows=[{"date": "2026-07-01", "tvl": 5_000_000.0}]
    )
    ok, md = dry_run(head, changed, client, "org", ALLOW, AS_OF)
    assert ok is True
    assert not client._datasets  # every provisioned dataset was deleted


def test_dry_run_off_allowlist_fails():
    head = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    head.functions[0].source.base_url = "https://evil.example"
    changed = {head.functions[0].function_id}
    client = FakeOsoClient(run_status="SUCCESS", query_rows=[{"tvl": 1.0}])
    ok, md = dry_run(head, changed, client, "org", ALLOW, AS_OF)
    assert ok is False and "allowlist" in md.lower()


def test_dry_run_failed_run_is_not_ok():
    head = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    changed = {head.functions[0].function_id}
    client = FakeOsoClient(run_status="FAILED", query_rows=[])
    ok, md = dry_run(head, changed, client, "org", ALLOW, AS_OF)
    assert ok is False
