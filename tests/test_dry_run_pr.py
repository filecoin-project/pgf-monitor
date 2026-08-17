from datetime import datetime, timezone

import pytest

from fpm.manifest import (
    FunctionSpec,
    Manifest,
    SlaSpec,
    SourceSpec,
    TransformSpec,
    load_manifest,
)
from fpm.oso.client import FakeOsoClient
from fpm.provision import dataset_name
from scripts.dry_run_pr import changed_function_ids, dry_run

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
ALLOW = {"api.llama.fi", "api.drand.sh", "filfox.info"}


def _transform_manifest():
    """A manifest whose only function computes its value in SQL, not with an extract."""
    return Manifest(
        team="tteam",
        maintainers=["@someone"],
        functions=[
            FunctionSpec(
                function_id="p95",
                tier="essential",
                sla=SlaSpec(
                    statement="p95 under 500ms",
                    metric="p95_latency_ms",
                    threshold_op="<=",
                    threshold_value=500.0,
                    cadence="daily",
                ),
                source=SourceSpec(
                    adapter="oso",
                    kind="http-json",
                    base_url="https://api.llama.fi",
                    query="/metrics",
                    extract=None,
                ),
                transform=TransformSpec(sql="SELECT max(latency_ms) FROM raw"),
            )
        ],
    )


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


def test_dry_run_leaves_the_production_dataset_alone():
    """The durable dataset the nightly observes from must survive a dry-run untouched.

    It used to be reused by name and then deleted in a `finally`, so labelling a PR
    destroyed the production dataset for every function it touched — and an authenticated
    source cannot be recreated by the nightly runner, which holds no credential.
    """
    head = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    fn = head.functions[0]
    changed = {fn.function_id}
    client = FakeOsoClient(
        run_status="SUCCESS", query_rows=[{"date": "2026-07-01", "tvl": 5_000_000.0}]
    )
    production = dataset_name(head.team, fn.function_id)
    production_id = client.create_dataset("org", production, production)

    ok, _ = dry_run(head, changed, client, "org", ALLOW, AS_OF)

    assert ok is True
    assert client.find_dataset("org", production) == production_id


def test_dry_run_evaluates_a_transform_metric():
    """19 of the 32 adopted entries compute their value in SQL. The gate called
    reduce_rows(rows, fn.source.extract) unconditionally, so `extract=None` raised
    AttributeError and those PRs could never produce the live proof the gate demands."""
    head = _transform_manifest()
    changed = {head.functions[0].function_id}
    client = FakeOsoClient(run_status="SUCCESS", query_rows=[{"m": 480.0}])

    ok, md = dry_run(head, changed, client, "org", {"api.llama.fi"}, AS_OF)

    assert ok is True, md
    assert "480.0" in md


def test_dry_run_deletes_its_own_dataset_when_reading_back_raises():
    head = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    changed = {head.functions[0].function_id}

    class Exploding(FakeOsoClient):
        def query(self, sql: str) -> list[dict]:
            raise RuntimeError("trino is down")

    client = Exploding(run_status="SUCCESS", query_rows=[{"tvl": 1.0}])

    ok, _ = dry_run(head, changed, client, "org", ALLOW, AS_OF)

    assert ok is False
    assert not client._datasets


def test_dry_run_names_its_dataset_after_the_run_tag():
    """Cleanup keys off a name that cannot collide with a durable one, so a dry-run can
    only ever delete a dataset it created itself."""
    head = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    fn = head.functions[0]
    changed = {fn.function_id}
    seen: list[str] = []

    class Recording(FakeOsoClient):
        def create_dataset(self, org_id: str, name: str, display_name: str) -> str:
            seen.append(name)
            return super().create_dataset(org_id, name, display_name)

    client = Recording(run_status="SUCCESS", query_rows=[{"tvl": 1.0}])

    dry_run(head, changed, client, "org", ALLOW, AS_OF, run_tag="pr42")

    assert seen == [f"{dataset_name(head.team, fn.function_id)}_pr42"]


def test_dry_run_cannot_be_given_a_run_tag_that_collides_with_a_durable_name():
    head = load_manifest("tests/fixtures/chainsafe_oso.yaml")
    client = FakeOsoClient(run_status="SUCCESS", query_rows=[{"tvl": 1.0}])
    with pytest.raises(ValueError):
        dry_run(head, set(), client, "org", ALLOW, AS_OF, run_tag="")


def test_dry_run_defaults_to_measuring_today():
    """The gate's job is proving the metric works NOW. It defaulted to --as-of 2026-07-01, so a
    windowed metric was 'proven' against a window weeks in the past."""
    from scripts.dry_run_pr import resolve_as_of

    assert resolve_as_of("").date() == datetime.now(timezone.utc).date()
    assert resolve_as_of("2026-07-01") == AS_OF
