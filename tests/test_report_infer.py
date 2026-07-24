"""Test the INFER call interface: intent + probe -> source proposal."""

from fpm.report.infer import INFER_JSON_SCHEMA, FakeSourceInferrer
from fpm.report.probe import probe


def _p():
    return probe(
        "https://api.llama.fi/v2/historicalChainTvl/Filecoin",
        lambda _u: (200, b'[{"date":"1","tvl":3959739.0}]'),
    )


def test_fake_infers_defillama_shape():
    out = FakeSourceInferrer().infer("Filecoin chain TVL should stay healthy", _p())
    assert out.kind == "http-json"
    assert out.extract.column == "tvl" and out.extract.reduce == "latest"
    assert out.extract.timestamp_column == "date"
    assert out.metric == "chain_tvl_usd" and out.confidence == "high"


def test_fake_low_confidence_on_unknown_shape():
    p = probe("https://x/y", lambda _u: (200, b'{"weird": 1}'))
    out = FakeSourceInferrer().infer("something", p)
    assert out.confidence == "low"


def test_inference_has_no_threshold_field():
    assert "threshold" not in INFER_JSON_SCHEMA["properties"]
    assert set(INFER_JSON_SCHEMA["properties"]) >= {
        "kind",
        "base_url",
        "endpoint",
        "extract",
        "metric",
        "confidence",
    }


def test_fake_exposes_metadata():
    s = FakeSourceInferrer()
    assert s.model_id == "fake" and s.prompt_version == "0"
