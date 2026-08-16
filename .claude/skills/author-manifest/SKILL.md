---
name: author-manifest
description: Use when a team encodes an already-agreed metric set into its own kernel-monitoring manifest — covers finding or starting the draft, choosing metrics/sources, validating offline, promoting, and opening the PR. Acting FOR one team, editing only their file. Triggers on "adopt our manifest", "add a metric", "change our SLA", "update our draft". For deciding what a team should be measured on in the first place, or making the agreement and registry agree, use `reconcile-metrics` instead.
---

# Author a kernel-monitoring manifest

You are acting for ONE team. Never touch another team's file.

This skill assumes the commitment is already agreed and your job is to encode it. If you are still
deciding *what* to measure, or the signed agreement and the manifest disagree, that is
`reconcile-metrics`.

## New here? Read this first

**`docs/guide-projects.md` is the long-form version of this skill, written for teams** — read it
first if anything below is unfamiliar; `README.md` covers the program in five minutes.

A **manifest** is `registry/<team>.yaml`: your public declaration of which **kernel functions**
(from the catalogue in `registry/_kernel.yaml`) you maintain, and for each one a **metric**, a
**public source** to read it from, and an **SLA** — the threshold you commit to. The pipeline
fetches your source on a schedule, judges it against that threshold, and publishes the verdict.
A **draft** under `registry/drafts/` is the same file before the team has confirmed it; promoting
turns it into an adopted manifest.

Prerequisites: `uv sync` once. **Everything here runs offline** except the final pull request —
you need no credentials to author and validate a manifest.

## Workflow

1. **Locate**: edit `registry/<team>.yaml` if the team is already adopted, or start a new
   `registry/drafts/<team>.yaml` (drafts are created on demand — none are pre-populated).
   Copy the structure of `registry/chainsafe.yaml` and read `docs/guide-projects.md` §2
   for the contract.

2. **Understand the function**: the entry's (tier, category, sub_category) MUST be
   copied character-for-character from `registry/_kernel.yaml`. Read the matching
   entry's `value:` text — your metric must evidence THAT, not general popularity.

3. **Ground the source choice (optional)**: before settling for a GitHub-activity proxy,
   check whether the project documents a real liveness surface. Filoscope indexes Filecoin
   docs, FIPs, specs and ecosystem code:

   ```bash
   npx -y --allow-remote=all filoscope pull                 # one-time ~479 MB
   npx -y --allow-remote=all -p filoscope qmd --index filoscope \
     search '<project> prometheus metrics endpoint port' -n 10
   npx -y --allow-remote=all -p filoscope qmd --index filoscope get '<docid>'
   rm -rf ~/.cache/qmd ~/.config/qmd ~/.npm/_npx             # ALWAYS purge when done
   ```

   Use `search`, never `query` — `query` pulls 2.2 GB of local models and stalls on CPU.
   `-c <collection>` is broken — the shipped `filoscope.yml` ships with `collections: {}`,
   so every name is rejected; filter `qmd://<namespace>/` with grep instead.
   A hit only counts if it is public, unauthenticated and HTTP-reachable: a Prometheus port
   on a self-hosted node is not monitorable. Filoscope suggests; the `curl` probe in the next
   step remains the only evidence. Skip this step entirely if the index is unavailable — it
   must never block authoring.

   Expect a low hit rate: a five-team probe of GitHub-proxy metrics turned up exactly one
   usable candidate. A null result is the normal outcome, not evidence you searched badly.

   It indexes repos, not deployments: Filoscope crawls repo contents, so it's blind to how
   a project is actually hosted. One probed team came back empty for this reason — its docs
   repo holds legacy static-site config while the live site is hosted elsewhere entirely.
   For a hosted surface, check the live site's headers directly rather than trusting the repo.

4. **Choose/verify the source**: public HTTP JSON. `curl` it NOW and confirm the exact
   fields. Record the probe (date, status, observed value) as a comment above the
   entry. Prefer the service's own surface over GitHub-activity proxies; GitHub
   release/commit cadence is an acceptable maintenance signal, not a liveness signal.

5. **Extract vs transform**: single field → `extract` (reduce/derive vocab in
   `registry/_schema.json`). Computation (lags vs wall clock, cadences, ratios) →
   `transform` (single SELECT, single scalar, table `raw` only; tz-aware ISO columns
   pair with `:now_tz`, unix-epoch columns with `:now` + `from_unixtime`). Nested JSON
   arrays are unreachable child tables — top-level fields only.

6. **Thresholds are commitments**: derive from the probe (observed 30s cadence →
   threshold 45s), state the rationale in a `# THRESHOLD:` comment. If uncertain, mark
   `PLACEHOLDER` and flag for the team/committee. `sla.threshold` is optional — omitting
   it entirely means "measured, not scored," the honest state when there is no agreement
   to point to. Give it `source: signed-appendix` only once you've read the number in the
   signed appendix; it defaults to `provisional`, and the dashboard labels provisional
   bars as such. Never invent a number just to fill the slot.

7. **Validate** (must be clean before any commit):
   ```bash
   uv run python scripts/validate_draft.py registry/drafts/<team>.yaml
   uv run pytest tests/test_drafts_conformance.py -q
   ```
   Allowlist `note` lines are fine IF the host is listed in
   `x_draft.allowlist_additions`; `FAIL` lines are not.

8. **Promote** (only when the team confirms thresholds + maintainers):
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
