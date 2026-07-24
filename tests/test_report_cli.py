from datetime import datetime, timezone

from fpm.report.cli_report import run_report_cli


def _fetch(_u):
    return 200, b'[{"date":"1","tvl":3959739.0}]'


def test_cli_report_prints_value_and_draft(capsys, tmp_path):
    code = run_report_cli(
        team="chainsafe",
        link="https://api.llama.fi/v2/historicalChainTvl/Filecoin",
        intent="Filecoin chain TVL",
        function_id="filecoin-tvl",
        as_of=datetime(2026, 7, 1, tzinfo=timezone.utc),
        out=str(tmp_path / "out.yaml"),
        live=False,
        fetch=_fetch,
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "chain_tvl_usd" in out and "3959739" in out
    assert "TODO(committee): set threshold" in (tmp_path / "out.yaml").read_text()
