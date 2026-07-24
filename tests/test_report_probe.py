from pathlib import Path

from fpm.report.probe import probe


def _fetch_ok(_url):
    return 200, Path("fixtures/report/defillama_sample.json").read_bytes()


def test_probe_list_series():
    p = probe("https://api.llama.fi/v2/historicalChainTvl/Filecoin", _fetch_ok)
    assert p.http_status == 200
    assert p.series_hint == "list"
    assert "tvl" in p.top_level_keys and "date" in p.top_level_keys
    assert isinstance(p.sample_json, list) and p.sample_json[-1]["tvl"] == 3959739.0


def test_probe_scalar():
    p = probe("https://x/y", lambda _u: (200, b'{"value": 5}'))
    assert p.series_hint == "dict"
    assert "value" in p.top_level_keys
