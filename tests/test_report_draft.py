from datetime import datetime, timezone

from fpm.report.draft import draft_function_yaml, validate_source
from fpm.report.infer import FakeSourceInferrer
from fpm.report.probe import probe

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _inf():
    p = probe("https://api.llama.fi/x", lambda _u: (200, b'[{"date":"1","tvl":1.0}]'))
    return FakeSourceInferrer().infer("Filecoin chain TVL", p)


def test_draft_omits_threshold_and_flags_todo():
    y = draft_function_yaml(_inf(), "Filecoin chain TVL", "filecoin-tvl")
    assert "threshold:" not in y  # the real schema key is omitted
    assert "TODO(committee): set threshold" in y
    assert "chain_tvl_usd" in y and "api.llama.fi" in y


def test_draft_includes_extract_path():
    y = draft_function_yaml(_inf(), "Filecoin chain TVL", "filecoin-tvl")
    assert "path:" in y


def test_validate_source_clean_on_allowlisted():
    warns = validate_source(_inf(), "chainsafe", {"api.llama.fi"}, AS_OF)
    assert warns == []


def test_validate_source_warns_off_allowlist():
    warns = validate_source(_inf(), "chainsafe", {"example.com"}, AS_OF)
    assert any("allowlist" in w.lower() for w in warns)
