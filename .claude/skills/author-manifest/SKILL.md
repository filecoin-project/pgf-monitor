---
name: author-manifest
description: Use when a team wants to create, adopt, or edit their kernel-monitoring manifest — covers finding the pre-populated draft, choosing metrics/sources, validating offline, promoting, and opening the PR. Triggers on "adopt our manifest", "add a metric", "change our SLA", "update our draft".
---

# Author a kernel-monitoring manifest

You are acting for ONE team. Never touch another team's file.

## Workflow

1. **Locate**: edit `registry/<team>.yaml` if the team is already adopted, or start a new
   `registry/drafts/<team>.yaml` (drafts are created on demand — none are pre-populated).
   Copy the structure of `registry/chainsafe.yaml` and read `docs/guide-projects.md` §2
   for the contract.

2. **Understand the function**: the entry's (tier, category, sub_category) MUST be
   copied character-for-character from `registry/_kernel.yaml`. Read the matching
   entry's `value:` text — your metric must evidence THAT, not general popularity.

3. **Choose/verify the source**: public HTTP JSON. `curl` it NOW and confirm the exact
   fields. Record the probe (date, status, observed value) as a comment above the
   entry. Prefer the service's own surface over GitHub-activity proxies; GitHub
   release/commit cadence is an acceptable maintenance signal, not a liveness signal.

4. **Extract vs transform**: single field → `extract` (reduce/derive vocab in
   `registry/_schema.json`). Computation (lags vs wall clock, cadences, ratios) →
   `transform` (single SELECT, single scalar, table `raw` only; tz-aware ISO columns
   pair with `:now_tz`, unix-epoch columns with `:now` + `from_unixtime`). Nested JSON
   arrays are unreachable child tables — top-level fields only.

5. **Thresholds are commitments**: derive from the probe (observed 30s cadence →
   threshold 45s), state the rationale in a `# THRESHOLD:` comment. If uncertain, mark
   `PLACEHOLDER` and flag for the team/committee.

6. **Validate** (must be clean before any commit):
   ```bash
   uv run python scripts/validate_draft.py registry/drafts/<team>.yaml
   uv run pytest tests/test_drafts_conformance.py -q
   ```
   Allowlist `note` lines are fine IF the host is listed in
   `x_draft.allowlist_additions`; `FAIL` lines are not.

7. **Promote** (only when the team confirms thresholds + maintainers):
   ```bash
   uv run python scripts/promote_draft.py registry/drafts/<team>.yaml --add-allowlist
   git rm registry/drafts/<team>.yaml
   ```
   Then branch, commit (`feat(registry): <team> ...`), `gh pr create`. Tell the user
   the committee must apply the `dry-run-ok` label for the live pre-merge check.

## Unmeasurable work

Coordination/quality work with no machine-checkable signal goes in
`x_draft.unmeasured` with a one-line reason. Do NOT invent proxy metrics for it —
an honest gap beats theater. Auth-gated sources go in `x_draft.candidates` with
`auth.secret_ref` noted (the committee provisions secrets).
