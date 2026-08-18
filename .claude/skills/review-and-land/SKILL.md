---
name: review-and-land
description: Use when a ProPGF reviewer wants to run the monitoring pipeline over metrics that are already flowing — check the readings, adjudicate recommendations, land verdicts to the warehouse, or produce a health report. Reviews READINGS, not the choice of metric. Triggers on "run the review", "are the metrics flowing", "land the verdicts", "kernel health report". To review or change which metrics a team is held to, use `reconcile-metrics`.
---

# Review a team and land verdicts

You are acting for the committee. The model's recommendation is ADVISORY — a human
(the user) adjudicates unless they explicitly ask for `--dev-auto-approve`.

Scope: this skill judges **readings against thresholds that already exist**. Whether the threshold
or the source is the right one is `reconcile-metrics`.

## New here? Read this first

`README.md` explains the program; `docs/guide-reviewers.md` is the full committee playbook this
skill condenses. Vocabulary used throughout: a **manifest** (`registry/<team>.yaml`) is one team's
declaration of the kernel functions it maintains and the threshold it commits to for each; **the
registry** is all of `registry/`; an **SLA outcome** is one reading judged against one threshold;
**landing** writes those verdicts to the OSO warehouse where the committee and community can query
them.

Prerequisites:

- `uv sync` once.
- **Everything below is runnable offline** with fixtures — start there (step 2's first command)
  before touching anything live.
- Live runs only: a `.env` at the repo root holding `OSO_API_KEY`, and the org UUID. Ask the user
  for both if you don't have them; never echo the key. No credentials means you can still do
  step 1 and the offline demo, which is enough to learn the shape.

## Workflow

1. **Registry sanity** (offline, always first):
   ```bash
   uv run pytest -q
   uv run python scripts/validate_draft.py --all
   ```

2. **Run the review**. Offline fixture demo — no credentials, no network:
   ```bash
   uv run fpm review chainsafe --manifest tests/fixtures/chainsafe.yaml --store /tmp/s \
     --dev-auto-approve          # drop this flag to adjudicate each result yourself
   ```
   Without `--dev-auto-approve` the command **prompts for each recommendation and blocks**; run
   non-interactively (an agent, a pipe, CI) it dies on `EOFError`. That is the flag's only correct
   use — a learning run. Never use it on a real review.
   Live (asks the user for the org UUID if unknown; filecoin = 35c17c26-4aa8-47ba-ba75-be8fe1e3718c):
   ```bash
   export $(grep -v '^#' .env | xargs)   # OSO_API_KEY; never echo it
   uv run fpm review <team> --live --live-oso --oso-org <uuid> --store .fpm_store
   ```
   Present each recommendation to the user for adjudication (approve/revise/reject/defer)
   — do not auto-approve on their behalf.

3. **Interpret outcomes**: `pass` fine · `fail` = SLA breach, check observed vs threshold
   and whether the source itself moved · `indeterminate` = the source produced no
   defensible number (look at `source_metadata` for `transform_error` / fetch errors;
   this is a data problem, not automatically a team problem).

4. **Land** (writes warehouse tables; confirm with the user before running):
   ```bash
   uv run fpm land --store .fpm_store --oso-org <uuid>
   ```
   Defaults land `filpgf_sla_verdicts` (public) + `filpgf_sla_verdicts_private`.
   NEVER use `--public-name filpgf_public` — that name belongs to a pre-existing UDM.
   A store built with `--dev-auto-approve` raises `UnadjudicatedVerdictError` and lands
   nothing: re-run the review and adjudicate the calls, rather than reaching for a flag.

5. **Report**: query `filecoin.filpgf_sla_verdicts.filpgf_sla_verdicts` (team,
   function_id, metric, observed_value, sla_outcome, adjudicated_status) and summarize
   breaches/indeterminates with their evidence. The dashboard
   (`dashboards/propgf-kernel-health.py`) is the visual companion.

## PR review (manifest changes)

Static gate output → goalpost report (`MATERIAL`/`loosened` lines need committee eyes)
→ if sound, the committee applies the `dry-run-ok` label for the live pre-merge fetch →
CODEOWNERS approval. Allowlist additions ride the same PR and are part of what is
being approved.
