"""Quarantined live OSO end-to-end. Never imported by unit tests. Requires OSO_API_KEY + org id.

Usage: OSO_API_KEY=... uv run python scripts/live_oso_smoke.py <ORG_ID>
Creates a throwaway ingestion in the given org, runs it, reads back, derives the observed
value exactly as the pipeline does, prints provenance, then deletes the dataset. Persists
nothing to the local store.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone

from fpm.domain import window_for
from fpm.manifest import load_manifest
from fpm.oso.graphql_client import GraphqlOsoClient
from fpm.provision import build_ingestion_config, dataset_name
from fpm.reduce import derive_observed

_TERMINAL = {"SUCCESS", "FAILED", "CANCELED"}


def main() -> None:
    org_id = sys.argv[1]
    # The one live guard on the ingestion trigger/poll path -- keep it pointed at a function
    # that EXISTS. It was still asking for `filecoin-tvl`, retired months ago, so the script
    # raised StopIteration before it ever reached `trigger_run`; that is why nobody caught OSO
    # changing the mutation payload on 2026-08-22 until three nights of readings were lost.
    fn = next(
        f
        for f in load_manifest("registry/chainsafe.yaml").functions
        if f.function_id == "mainnet-snapshot-freshness"
    )
    window = window_for(fn.sla.cadence, datetime(2026, 7, 1, tzinfo=timezone.utc))
    client = GraphqlOsoClient(api_key=os.environ["OSO_API_KEY"], org_id=org_id)

    name = dataset_name("chainsafe", fn.function_id)
    dataset_id = client.find_dataset(org_id, name) or client.create_dataset(org_id, name, name)
    try:
        client.attach_rest_config(dataset_id, build_ingestion_config(fn, window, "chainsafe"))
        run_id = client.trigger_run(dataset_id)
        run = None
        for _ in range(30):
            runs = {r.run_id: r for r in client.get_runs(dataset_id)}
            run = runs.get(run_id)
            print("run status:", run.status if run else "unknown")
            if run and run.status in _TERMINAL:
                break
            time.sleep(10)
        if run and run.status == "SUCCESS":
            full = client.table_full_name(dataset_id)
            rows = client.query(f"SELECT * FROM {full}")
            # derive_observed, NOT reduce_rows. reduce_rows implements `derive: value` only;
            # for the `derive: age_seconds` metric this smoke points at, it returns the latest
            # ROW and float()s a timestamp string -- so the script always ended in a traceback
            # AFTER the trigger/poll path it exists to guard had already passed. A guard that
            # always ends red is a guard nobody runs, which is exactly how this script rotted
            # the first time (it asked for `filecoin-tvl`, retired months earlier, and raised
            # StopIteration before reaching trigger_run -- so nobody caught OSO changing the
            # mutation payload on 2026-08-22 until three nights of readings were gone).
            # The real pipeline calls derive_observed; so must this, or it is not the same test.
            value = derive_observed(rows, fn.source.extract, datetime.now(timezone.utc))
            print("table:", full)
            print("observed:", value)
        else:
            print("run did not succeed; would yield indeterminate")
    finally:
        client.delete_dataset(dataset_id)
        print("cleanup: deleted", dataset_id)


if __name__ == "__main__":
    main()
