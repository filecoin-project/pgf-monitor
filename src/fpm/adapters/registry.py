from __future__ import annotations

from pathlib import Path

from fpm.adapters.base import Adapter
from fpm.adapters.fixture import FixtureAdapter


class UnsupportedAdapterError(ValueError):
    """Raised when a manifest declares an adapter the runtime does not provide."""


def build_adapters(
    fixtures_dir: Path,
    oso_client=None,
    org_id: str = "",
    allowlist: set[str] | None = None,
    poll_sleep: float = 0.0,
    sql_allowlist: set[str] | None = None,
) -> dict[str, Adapter]:
    """The adapters a run may use. `allowlist` gates egress hosts, `sql_allowlist` warehouse tables.

    Both default to EMPTY rather than permissive: a runtime built without the committee lists
    must refuse every host and every table, not accept them all.
    """
    registry: dict[str, Adapter] = {"fixture": FixtureAdapter(fixtures_dir)}
    if oso_client is not None:
        from fpm.adapters.oso import OsoAdapter
        from fpm.adapters.oso_sql import OsoSqlAdapter

        registry["oso"] = OsoAdapter(
            oso_client, org_id=org_id, allowlist=allowlist or set(), poll_sleep=poll_sleep
        )
        registry["oso-sql"] = OsoSqlAdapter(oso_client, allowed_tables=sql_allowlist or set())

    class _Registry(dict):
        def __missing__(self, key: str):
            raise UnsupportedAdapterError(f"no adapter registered for {key!r}")

    return _Registry(registry)
