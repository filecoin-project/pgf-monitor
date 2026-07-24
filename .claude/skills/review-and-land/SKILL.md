---
name: review-and-land
description: Use when a ProPGF reviewer wants to check that metrics are flowing, run a review over a team, adjudicate recommendations, land verdicts to the warehouse, or produce a health report. Triggers on "run the review", "are the metrics flowing", "land the verdicts", "kernel health report".
---

# Review a team and land verdicts

You are acting for the committee. The model's recommendation is ADVISORY — a human
(the user) adjudicates unless they explicitly ask for `--dev-auto-approve`.

## Workflow

1. **Registry sanity** (offline, always first):
   ```bash
   uv run pytest -q
   uv run python scripts/validate_draft.py --all
   ```

2. **Run the review**. Offline fixture demo: `uv run fpm review chainsafe --manifest tests/fixtures/chainsafe.yaml --store /tmp/s`.
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

5. **Report**: query `filecoin.filpgf_sla_verdicts.filpgf_sla_verdicts` (team,
   function_id, metric, observed_value, sla_outcome, adjudicated_status) and summarize
   breaches/indeterminates with their evidence. The dashboard
   (`dashboards/propgf-kernel-health.py`) is the visual companion.

## PR review (manifest changes)

Static gate output → goalpost report (`MATERIAL`/`loosened` lines need committee eyes)
→ if sound, the committee applies the `dry-run-ok` label for the live pre-merge fetch →
CODEOWNERS approval. Allowlist additions ride the same PR and are part of what is
being approved.
