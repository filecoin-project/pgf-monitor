from fpm.report.apply import observed_value
from fpm.report.infer import ExtractProposal, FakeSourceInferrer, InferenceOutput
from fpm.report.probe import probe


def test_apply_defillama_latest():
    p = probe(
        "https://api.llama.fi/x",
        lambda _u: (200, b'[{"date":"1","tvl":3800000.0},{"date":"2","tvl":3959739.0}]'),
    )
    out = FakeSourceInferrer().infer("tvl", p)
    assert observed_value(out, p) == 3959739.0


def test_apply_scalar_dict_single():
    p = probe("https://x/y", lambda _u: (200, b'{"value": 5}'))
    out = FakeSourceInferrer().infer("v", p)  # low-confidence single over "value"
    assert observed_value(out, p) == 5.0


def test_apply_age_days_derive_returns_age_not_epoch():
    # Direct InferenceOutput construction (the Fake never emits derive != "value").
    p = probe("https://x/y", lambda _u: (200, b'{"updated_at": "2020-01-01T00:00:00+00:00"}'))
    out = InferenceOutput(
        kind="http-json",
        base_url=p.url,
        endpoint=p.url,
        extract=ExtractProposal(
            column="updated_at", cast="date", reduce="single", derive="age_days"
        ),
        metric="staleness_days",
        rationale="age of the updated_at timestamp, in days",
        confidence="low",
    )
    v = observed_value(out, p)
    assert v is not None
    assert 0 < v < 100_000  # a plausible day count, not a raw epoch (which is > 1_000_000)
    assert v < 1_000_000


def test_apply_nested_path_descends_before_reducing():
    p = probe("https://x/y", lambda _u: (200, b'{"data": [{"x": 5}]}'))
    out = InferenceOutput(
        kind="http-json",
        base_url=p.url,
        endpoint=p.url,
        extract=ExtractProposal(path="$.data", column="x", reduce="single"),
        metric="x",
        rationale="nested under data",
        confidence="low",
    )
    assert observed_value(out, p) == 5.0
