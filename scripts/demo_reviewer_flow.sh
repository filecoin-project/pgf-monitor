#!/usr/bin/env bash
# Demo: the committee's review loop, end to end. Offline by default; if OSO_API_KEY is
# set, the final step also queries the live verdict table in the warehouse.
set -euo pipefail
cd "$(dirname "$0")/.."

STORE="$(mktemp -d)"
trap 'rm -rf "$STORE"' EXIT

step() { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }

step "1/4 Registry sanity: PR gate on a manifest + full deterministic suite"
uv run python -m scripts.validate_pr registry/chainsafe.yaml | tail -25
uv run pytest -q | tail -1

step "2/4 Run a review over a fixture-backed manifest snapshot — no network needed"
# The real registry/chainsafe.yaml now carries live sources; the offline demo reviews
# the committed fixture snapshot instead. --dev-auto-approve for demo determinism.
uv run fpm review chainsafe --manifest tests/fixtures/chainsafe.yaml \
    --store "$STORE" --dev-auto-approve

step "3/4 Verdicts persisted as ReviewBundles (evidence-hashed, replayable)"
ls "$STORE"
uv run python - "$STORE" <<'PY'
import sys
from pathlib import Path
from fpm.store import JsonlRecordStore
for b in JsonlRecordStore(Path(sys.argv[1])).all_bundles():
    r = b.recommendation
    print(f"  {r.team}/{r.function_id}: outcome={b.dossier.sla_result.outcome} "
          f"recommendation={r.review_status} verdict={b.verdict.adjudicated_status}")
PY

step "4/4 Land + query (live, only if OSO_API_KEY is set)"
if [ -n "${OSO_API_KEY:-}" ] && [ -n "${DEMO_LIVE:-}" ]; then
    uv run fpm land --store "$STORE" --oso-org "${OSO_ORG_ID:?set OSO_ORG_ID}"
    uv run python - <<'PY'
from pyoso import Client
df = Client().to_pandas(
    "SELECT team, function_id, metric, observed_value, sla_outcome "
    "FROM filecoin.filpgf_sla_verdicts.filpgf_sla_verdicts ORDER BY team, function_id"
)
print(df.to_string(index=False))
PY
else
    echo "  (skipped: set OSO_API_KEY, OSO_ORG_ID and DEMO_LIVE=1 to land + query for real)"
    echo "  land command:  uv run fpm land --store <store> --oso-org <org-uuid>"
    echo "  query:         SELECT ... FROM filecoin.filpgf_sla_verdicts.filpgf_sla_verdicts"
fi

printf '\n\033[1;36mDone.\033[0m Dashboard: uv sync --extra dashboards && uv run marimo run dashboards/propgf-kernel-health.py\n'
