from datetime import datetime, timezone

from fpm.adapters.oso import OsoAdapter
from fpm.domain import window_for
from fpm.evaluate import evaluate_sla
from fpm.manifest import FunctionSpec, SlaSpec, SourceSpec, TransformSpec
from fpm.oso.client import FakeOsoClient

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
ALLOW = {"api.llama.fi"}


def _transform_fn(sql="SELECT approx_percentile(latency_ms, 0.95) FROM raw"):
    return FunctionSpec(
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
        transform=TransformSpec(sql=sql),
    )


def test_transform_path_reads_scalar():
    fn = _transform_fn()
    client = FakeOsoClient(run_status="SUCCESS", query_rows=[{"m": 480.0}])
    adapter = OsoAdapter(client, org_id="org", allowlist=ALLOW)
    reading = adapter.fetch(fn, "team", window_for(fn.sla.cadence, AS_OF))
    assert reading.claim.value == 480.0
    assert reading.claim.evidence is not None
    assert evaluate_sla(reading, fn, "team").outcome == "pass"
    assert "transform_error" not in reading.source_metadata


def test_invalid_transform_sql_yields_indeterminate():
    fn = _transform_fn(sql="SELECT count(*) FROM oso.projects_v1")  # foreign table
    client = FakeOsoClient(run_status="SUCCESS", query_rows=[{"m": 1.0}])
    adapter = OsoAdapter(client, org_id="org", allowlist=ALLOW)
    reading = adapter.fetch(fn, "team", window_for(fn.sla.cadence, AS_OF))
    assert reading.claim.value is None
    assert evaluate_sla(reading, fn, "team").outcome == "indeterminate"
    transform_error = reading.source_metadata.get("transform_error")
    assert transform_error
    assert "transform" in transform_error


def test_non_scalar_result_yields_indeterminate():
    fn = _transform_fn()
    client = FakeOsoClient(run_status="SUCCESS", query_rows=[])  # no rows back
    adapter = OsoAdapter(client, org_id="org", allowlist=ALLOW)
    reading = adapter.fetch(fn, "team", window_for(fn.sla.cadence, AS_OF))
    assert reading.claim.value is None
    assert evaluate_sla(reading, fn, "team").outcome == "indeterminate"
