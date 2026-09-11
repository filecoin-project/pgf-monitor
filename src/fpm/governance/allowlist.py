"""Egress host and warehouse table allowlists. Read from the base ref by callers, never the PR head.

Two lists, two regimes: hosts gate what an http-json source may FETCH, warehouse tables gate what
an `oso-sql` source may READ. Same governance discipline — committee-maintained, CODEOWNERS-
guarded, and an addition must land in an earlier PR than the metric that needs it.
"""

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


def load_sql_allowlist(path: str | Path) -> set[str]:
    """Warehouse tables an `oso-sql` metric may read: fully-qualified catalog.schema.table.

    Lowercased on load so membership never depends on how a line was typed; `validate_warehouse_sql`
    normalizes again, because a caller may build the set some other way.
    """
    tables: set[str] = set()
    for line in Path(path).read_text().splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            tables.add(s.lower())
    return tables
