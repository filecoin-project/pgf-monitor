"""Egress host allowlist. Read from the base ref by callers, never the PR head."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


def host_of(base_url: str) -> str | None:
    return urlparse(base_url).hostname if base_url else None


def load_allowlist(path: str | Path) -> set[str]:
    hosts: set[str] = set()
    for line in Path(path).read_text().splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            hosts.add(s)
    return hosts


def host_allowed(base_url: str, allowlist: set[str]) -> bool:
    host = host_of(base_url)
    return host is not None and host in allowlist
