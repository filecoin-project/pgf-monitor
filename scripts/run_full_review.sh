#!/usr/bin/env bash
#
# run_full_review.sh — the canonical FULL monitoring run, as one reproducible command.
#
# Reviews every registry team and appends + uploads both the thresholds and observations time
# series. It does NOT land verdicts — see below. The INVOCATION is deterministic (fixed
# team order + fixed flags), so an agent can run it identically every time. The RESULTS are not
# deterministic, by design:
#   - live readings change run-to-run (that is what monitoring is);
#   - GitHub's 60/hr unauth rate limit makes some GitHub-sourced functions read
#     `indeterminate` non-deterministically — provision a committee token via a source
#     `auth.secret_ref` to remove that flake;
#   - with --synth live the advisory narrative is model-generated (varies); --synth fake
#     (the default here) is deterministic and writes no narrative.
#
# THIS WRAPPER LANDS NOTHING. It passes --dev-auto-approve, so every recommendation in $STORE
# is stamped approver="dev-auto" — a development convenience, not an adjudication. It used to
# run `fpm land` anyway, which meant the PUBLIC verdict table could carry rows no human ever
# read, and a partial table whenever a team failed. `fpm land` now REFUSES a dev-auto batch
# (fpm.land.assert_adjudicated), so landing verdicts means reviewing teams individually per
# docs/guide-reviewers.md §2 and adjudicating each call yourself.
#
# What it does refresh is measurement, not judgment: the observations and thresholds series,
# which carry no verdict.
#
# Usage:
#   export OSO_API_KEY=<org-scoped key>        # required
#   scripts/run_full_review.sh [--oso-org UUID] [--store DIR] [--synth fake|live] [--as-of YYYY-MM-DD]
#
# Defaults: --oso-org $OSO_ORG or the filecoin org UUID; --store .fpm_store (recreated fresh
# each run); --synth fake (deterministic, no LLM); --as-of today (UTC).
#
set -euo pipefail
cd "$(dirname "$0")/.."

OSO_ORG_ID="${OSO_ORG:-35c17c26-4aa8-47ba-ba75-be8fe1e3718c}"
STORE=".fpm_store"
SYNTH="fake"
AS_OF="$(date -u +%F)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --oso-org) OSO_ORG_ID="$2"; shift 2 ;;
    --store)   STORE="$2";      shift 2 ;;
    --synth)   SYNTH="$2";      shift 2 ;;
    --as-of)   AS_OF="$2";      shift 2 ;;
    -h|--help) sed -n '2,32p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

: "${OSO_API_KEY:?set OSO_API_KEY (org-scoped) before running}"

SYNTH_FLAG="--live"                       # real SDK narrative
[[ "$SYNTH" == "fake" ]] && SYNTH_FLAG="" # deterministic, no LLM
if [[ "$SYNTH" != "fake" && "$SYNTH" != "live" ]]; then
  echo "--synth must be 'fake' or 'live'" >&2; exit 2
fi

# fresh store so this run's verdicts/observations reflect only this run
rm -rf "$STORE"; mkdir -p "$STORE"

# deterministic team list: every registry/*.yaml except _-prefixed helpers, sorted
mapfile -t TEAMS < <(ls registry/*.yaml | grep -v '/_' | xargs -n1 basename | sed 's/\.yaml$//' | sort)

echo "== full review: ${#TEAMS[@]} teams | store=$STORE | org=$OSO_ORG_ID | synth=$SYNTH | as-of=$AS_OF =="

fails=0
for t in "${TEAMS[@]}"; do
  echo "---- review: $t"
  # shellcheck disable=SC2086  # SYNTH_FLAG is intentionally word-split (empty or --live)
  if ! uv run fpm review "$t" $SYNTH_FLAG --live-oso --oso-org "$OSO_ORG_ID" \
        --store "$STORE" --as-of "$AS_OF" --dev-auto-approve; then
    echo "!! review failed for $t (continuing)" >&2
    fails=$((fails + 1))
  fi
done

# Upload order is load-bearing, not incidental (see docs/guide-reviewers.md §4):
#   1. upload-thresholds FIRST — creates/refreshes filpgf_sla_thresholds.
#   2. publish the notebook (a separate, held step this script does not run) — safe
#      against the OLD observations table, because the new query names only columns
#      that exist in both the old and narrowed schemas.
#   3. upload (observations) LAST — republishing this table narrows it to what the
#      notebook's committed query expects.
# Inverting this order leaves a window where the dashboard's obs_data cell hits the bare
# `except Exception` fallback (missing an "observations" entry) and every chart/uptime
# strip silently disappears.
echo "== append + upload thresholds and observations =="
uv run python scripts/observations.py append --store "$STORE"
uv run python scripts/observations.py upload-thresholds --oso-org "$OSO_ORG_ID"
uv run python scripts/observations.py upload --oso-org "$OSO_ORG_ID"

echo "== DONE: ${TEAMS[*]}"
echo "== reviewed ${#TEAMS[@]} teams ($fails review failure(s)); no verdicts landed; thresholds and observations uploaded =="
if [[ $fails -gt 0 ]]; then
  echo "NOTE: $fails team(s) failed review — usually the GitHub 60/hr unauth rate limit;" >&2
  echo "      provision a committee GitHub token via a source auth.secret_ref to reduce it." >&2
  # A partial run must not read as a clean one: the uploaded series is missing those teams.
  # The count is the useful part, so exit with it rather than a bare 1.
  exit "$fails"
fi
