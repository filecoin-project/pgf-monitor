"""Quarantined live OSO transform end-to-end. Never imported by unit tests. Requires OSO_API_KEY.

Provisions a real ingestion against the DeFiLlama Filecoin TVL endpoint, runs it, then computes a
rich metric via the bound transform SQL path (OsoAdapter._transform_value / bind_transform_sql) -
a ratio the extract reduce vocabulary cannot express - and prints the observed value plus the SLA
outcome. Cleans up the dataset afterward. Persists nothing to the local store.

Usage: OSO_API_KEY=... uv run python scripts/live_transform_smoke.py <ORG_ID>
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from fpm.adapters.oso import OsoAdapter
from fpm.domain import window_for
from fpm.evaluate import evaluate_sla
from fpm.governance.allowlist import load_allowlist
from fpm.manifest import FunctionSpec, SlaSpec, SourceSpec, TransformSpec
from fpm.oso.graphql_client import GraphqlOsoClient
from fpm.provision import dataset_name

_ALLOWLIST_PATH = "registry/_allowlist.txt"

# Ratio of the latest TVL reading to the average TVL over the full raw series - a rich metric not
# expressible with the extract reduce vocabulary (single/latest/avg/min/max/null_ratio). Avoids
# the :window_start/:window_end bind tokens entirely since DeFiLlama's `date` column is epoch
# seconds, not a TIMESTAMP.
TRANSFORM_SQL = "SELECT (SELECT tvl FROM raw ORDER BY date DESC LIMIT 1) / avg(tvl) FROM raw"


def _function_spec() -> FunctionSpec:
    return FunctionSpec(
        function_id="filecoin-tvl-ratio",
        tier="important",
        sla=SlaSpec(
            statement="Filecoin chain TVL latest/average ratio stays near 1, measured monthly",
            metric="chain_tvl_ratio",
            threshold_op=">=",
            threshold_value=0.0,
            cadence="monthly",
        ),
        source=SourceSpec(
            adapter="oso",
            kind="http-json",
            base_url="https://api.llama.fi",
            endpoint="https://api.llama.fi/v2/historicalChainTvl/Filecoin",
            query="/v2/historicalChainTvl/Filecoin",
            extract=None,
        ),
        transform=TransformSpec(sql=TRANSFORM_SQL),
    )


def main() -> None:
    org_id = sys.argv[1]
    team = "chainsafe"
    fn = _function_spec()
    window = window_for(fn.sla.cadence, datetime(2026, 7, 1, tzinfo=timezone.utc))
    allowlist = load_allowlist(_ALLOWLIST_PATH)
    client = GraphqlOsoClient(api_key=os.environ["OSO_API_KEY"], org_id=org_id)
    # A live dlt ingestion run takes tens of seconds to reach SUCCESS, so poll with a real wait
    # (the default poll_sleep=0.0 fires all attempts in a few seconds and times out). Matches the
    # 10s cadence in live_oso_smoke.py: up to 30 attempts x 10s.
    adapter = OsoAdapter(client, org_id=org_id, allowlist=allowlist, poll_sleep=10.0)

    name = dataset_name(team, fn.function_id)
    try:
        reading = adapter.fetch(fn, team, window)
        print("observed:", reading.claim.value)
        print("sla:", evaluate_sla(reading, fn, team))
    finally:
        dataset_id = client.find_dataset(org_id, name)
        if dataset_id is not None:
            client.delete_dataset(dataset_id)
            print("cleanup: deleted", dataset_id)


if __name__ == "__main__":
    main()
