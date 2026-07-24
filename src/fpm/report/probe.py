"""Probe a maintainer-provided source: a bounded HTTP GET, parsed into a Probe. fetch is injected."""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from typing import Literal

from fpm.domain import _Model

Fetch = Callable[[str], tuple[int, bytes]]
_MAX_BYTES = 2_000_000
_TIMEOUT = 15


class Probe(_Model):
    url: str
    http_status: int
    sample_json: object
    top_level_keys: list[str]
    series_hint: Literal["scalar", "list", "dict"]


def _http_fetch(url: str) -> tuple[int, bytes]:
    with urllib.request.urlopen(url, timeout=_TIMEOUT) as resp:  # noqa: S310 (maintainer's own source)
        return resp.status, resp.read(_MAX_BYTES)


def probe(url: str, fetch: Fetch = _http_fetch) -> Probe:
    status, body = fetch(url)
    payload = json.loads(body[:_MAX_BYTES])
    if isinstance(payload, list):
        hint = "list"
        keys = sorted(payload[0].keys()) if payload and isinstance(payload[0], dict) else []
    elif isinstance(payload, dict):
        hint = "dict"
        keys = sorted(payload.keys())
    else:
        hint = "scalar"
        keys = []
    return Probe(
        url=url, http_status=status, sample_json=payload, top_level_keys=keys, series_hint=hint
    )
