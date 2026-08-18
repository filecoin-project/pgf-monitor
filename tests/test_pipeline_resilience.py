from datetime import datetime, timezone
from pathlib import Path

from fpm.domain import ApprovalDecision
from fpm.oso.client import FakeOsoClient
from fpm.pipeline import run_review
from fpm.store import JsonlRecordStore
from fpm.synthesize import FakeReviewSynthesizer

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)

# bad-egress is processed FIRST and its host is not on the allowlist, so OsoAdapter.fetch raises
# EgressError. Before per-function isolation this aborted the whole run; the second function never
# ran. The good function's host is allowed and the fake client returns a value.
_MANIFEST = (
    "team: t\nmaintainers: [a]\nfunctions:\n"
    "  - function_id: bad-egress\n    kernel_id: chain-sync-state\n"
    "    funded_project_oso_slug: drand\n    tier: essential\n"
    "    category: 'Blockchain Core & Physical Storage'\n"
    "    sub_category: 'Ledger & Consensus'\n"
    "    sla: {statement: s, metric: m, threshold: {op: '>=', value: 0.5}, cadence: daily}\n"
    "    source: {adapter: oso, kind: http-json, base_url: 'https://blocked.example',"
    " query: /q, extract: {column: v, reduce: single}}\n"
    "  - function_id: good\n    kernel_id: chain-sync-state\n"
    "    funded_project_oso_slug: drand\n    tier: essential\n"
    "    category: 'Blockchain Core & Physical Storage'\n"
    "    sub_category: 'Ledger & Consensus'\n"
    "    sla: {statement: s, metric: m, threshold: {op: '>=', value: 0.5}, cadence: daily}\n"
    "    source: {adapter: oso, kind: http-json, base_url: 'https://ok.example',"
    " query: /q, extract: {column: v, reduce: single}}\n"
)


def test_one_function_error_does_not_abort_the_batch(tmp_path):
    manifest = tmp_path / "m.yaml"
    manifest.write_text(_MANIFEST)
    store = JsonlRecordStore(tmp_path / "out")
    bundles = run_review(
        manifest_path=manifest,
        fixtures_dir=Path("fixtures/responses"),
        synthesizer=FakeReviewSynthesizer(),
        store=store,
        decide=lambda r: ApprovalDecision(action="approve", approver="t"),
        as_of=AS_OF,
        oso_client=FakeOsoClient(run_status="SUCCESS", query_rows=[{"v": 1.0}]),
        org_id="org",
        allowlist={"ok.example"},  # blocks blocked.example -> EgressError on bad-egress
    )
    by = {b.recommendation.function_id: b for b in bundles}
    # both functions produced a verdict: the failure was isolated, not fatal
    assert set(by) == {"bad-egress", "good"}
    assert by["good"].recommendation.sla_outcome == "pass"
    assert by["bad-egress"].recommendation.sla_outcome == "indeterminate"
    assert "error" in str(by["bad-egress"].dossier.reading.source_metadata).lower()
