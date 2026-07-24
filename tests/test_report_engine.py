from datetime import datetime, timezone

from fpm.report.engine import run_report
from fpm.report.infer import FakeSourceInferrer

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _fetch(_u):
    return 200, b'[{"date":"1","tvl":3800000.0},{"date":"2","tvl":3959739.0}]'


def test_run_report_end_to_end():
    d = run_report(
        "Filecoin chain TVL should stay healthy",
        "https://api.llama.fi/v2/historicalChainTvl/Filecoin",
        team="chainsafe",
        function_id="filecoin-tvl",
        inferrer=FakeSourceInferrer(),
        allowlist={"api.llama.fi"},
        as_of=AS_OF,
        fetch=_fetch,
    )
    assert d.observed_value == 3959739.0
    assert d.metric == "chain_tvl_usd"
    assert "TODO(committee): set threshold" in d.manifest_yaml
    assert d.warnings == []  # allowlisted, high confidence, value present


def test_run_report_flags_off_allowlist_and_low_conf():
    d = run_report(
        "weird metric",
        "https://evil.example/x",
        team="t",
        function_id="f",
        inferrer=FakeSourceInferrer(),
        allowlist={"api.llama.fi"},
        as_of=AS_OF,
        fetch=lambda _u: (200, b'{"weird": 1}'),
    )
    assert any("allowlist" in w.lower() for w in d.warnings)
    assert any("confidence" in w.lower() for w in d.warnings)
