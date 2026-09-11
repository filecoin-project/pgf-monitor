"""Live proof that the `oso-sql` path reads a real number out of the warehouse.

Quarantined on purpose: never imported by tests, because it needs OSO_API_KEY and the network.
The offline suite covers the guard and the adapter (tests/test_transform_warehouse_sql.py,
tests/test_adapter_oso_sql.py); this asserts the one thing they cannot — that the SQL a manifest
declares actually runs against Trino and returns a single numeric cell.

    export OSO_API_KEY=...          # org-scoped key
    uv run python scripts/live_oso_sql_smoke.py

Also checks the negative: a private table is refused BEFORE any query is sent, which is the whole
reason the kind is allowed to exist. That assertion matters more than the value — the key this
script holds can genuinely read `funding_model_static.applicant_identity`, so if the guard ever
regressed, the query would succeed rather than fail.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from fpm.adapters.oso_sql import OsoSqlAdapter
from fpm.domain import window_for
from fpm.governance.allowlist import load_sql_allowlist
from fpm.manifest import load_manifest
from fpm.oso.graphql_client import GraphqlOsoClient
from fpm.transform.validate import TransformSqlError, validate_warehouse_sql

ORG = "35c17c26-4aa8-47ba-ba75-be8fe1e3718c"
FIXTURE = "tests/fixtures/filoz_oso_sql.yaml"


def main() -> int:
    if not os.environ.get("OSO_API_KEY"):
        print("OSO_API_KEY is not set", file=sys.stderr)
        return 2

    allowed = load_sql_allowlist("registry/_sql_allowlist.txt")
    print(f"allowlist: {len(allowed)} table(s)")
    for t in sorted(allowed):
        print(f"  {t}")

    # 1. the guard refuses a private table without touching the network
    private = "SELECT COUNT(*) FROM filecoin.funding_model_static.applicant_identity"
    try:
        validate_warehouse_sql(private, allowed)
    except TransformSqlError as exc:
        print(f"\nOK   private table refused before any query: {exc}")
    else:
        print("\nFAIL private table was ACCEPTED by the guard", file=sys.stderr)
        return 1

    # 2. the declared metric SQL runs and yields one number
    client = GraphqlOsoClient(api_key=os.environ["OSO_API_KEY"], org_id=ORG)
    fn = load_manifest(FIXTURE).functions[0]
    adapter = OsoSqlAdapter(client, allowed_tables=allowed)
    reading = adapter.fetch(fn, "filoz", window_for(fn.sla.cadence, datetime.now(timezone.utc)))

    if reading.claim.value is None:
        print(
            f"\nFAIL {fn.sla.metric}: {reading.source_metadata.get('sql_error')}", file=sys.stderr
        )
        return 1
    print(f"\nOK   {fn.sla.metric} = {reading.claim.value:,.2f}")
    print(f"     evidence bundle {reading.claim.evidence.evidence_bundle_hash[:16]}…")
    print(f"     run ref         {reading.claim.evidence.oso_run_ref}  (none, by design)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
