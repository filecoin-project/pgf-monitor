import pytest

from fpm.sdk_result import structured_payload


def test_prefers_structured_output():
    assert structured_payload({"a": 1}, '{"b": 2}') == {"a": 1}


def test_falls_back_to_plain_result_text():
    assert structured_payload(None, '{"answer": "hello"}') == {"answer": "hello"}


def test_strips_json_code_fence():
    assert structured_payload(None, '```json\n{"x": 1}\n```') == {"x": 1}


def test_extracts_brace_block_from_noisy_text():
    assert structured_payload(None, 'here you go: {"x": 1} thanks') == {"x": 1}


def test_raises_when_nothing_usable():
    with pytest.raises(RuntimeError):
        structured_payload(None, None)
    with pytest.raises(RuntimeError):
        structured_payload({}, "")
