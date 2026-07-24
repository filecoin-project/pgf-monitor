#!/usr/bin/env bash
# Demo: a funded team's manifest loop, end to end, offline, no credentials.
# Everything runs against a scratch copy — the repo is never mutated.
set -euo pipefail
cd "$(dirname "$0")/.."

TEAM="${1:-randamu}"
DRAFT="registry/drafts/${TEAM}.yaml"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

step() { printf '\n\033[1;32m== %s\033[0m\n' "$*"; }

if [ ! -f "$DRAFT" ]; then
    # No live draft (the 2026-07-15 batch was promoted) — synthesize a demo draft
    # from the team's adopted manifest so the flow stays runnable end-to-end.
    [ -f "registry/${TEAM}.yaml" ] || { echo "no draft or manifest for '${TEAM}'"; exit 1; }
    DRAFT="$WORK/${TEAM}-draft.yaml"
    awk '/^maintainers:/ { print; print "x_draft:\n  slate_status: \"demo\"\n  prepared_by: \"demo_project_flow.sh\"\n  allowlist_additions: []"; next } { print }' \
        "registry/${TEAM}.yaml" > "$DRAFT"
    echo "(no live draft — synthesized a demo draft from registry/${TEAM}.yaml)"
fi
grep -E "function_id:|metric:|statement:" "$DRAFT" | sed 's/^ *//' | head -12

step "2/5 Validate the draft offline (schema + kernel taxonomy + transform SQL + allowlist)"
uv run python scripts/validate_draft.py "$DRAFT"

step "3/5 Run the deterministic suite the PR gate runs"
uv run pytest tests/test_drafts.py tests/test_drafts_conformance.py -q

step "4/5 Dry promotion into a scratch registry (comments preserved, x_draft stripped)"
cp registry/_allowlist.txt "$WORK/allowlist.txt"
uv run python scripts/promote_draft.py "$DRAFT" \
    --allowlist "$WORK/allowlist.txt" --add-allowlist --out "$WORK/${TEAM}.yaml"
echo "--- promoted file head ---"
head -20 "$WORK/${TEAM}.yaml"

step "5/5 The static PR gate over the promoted manifest (what CI will run on your PR)"
uv run python -m scripts.validate_pr "$WORK/${TEAM}.yaml" --allowlist "$WORK/allowlist.txt"

printf '\n\033[1;32mDone.\033[0m For real: promote without --out, git rm the draft, open the PR.\n'
printf 'The committee applies the dry-run-ok label for the live pre-merge fetch.\n'
