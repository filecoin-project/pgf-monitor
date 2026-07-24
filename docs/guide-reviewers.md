# Reviewer guide — verify the metrics flow, run reviews, automate reports

For the ProPGF committee and anyone auditing the system. Like the project guide, you can
follow it yourself or hand it to a coding agent. Everything but the warehouse/live steps
runs offline.

## The pipeline in one line

manifest (repo) → fetch via OSO ingestion → SLA evaluation → manipulation detectors →
bounded model recommendation → **human adjudication** → verdicts landed to the warehouse.

The repo is the trust anchor: every measurement period pins the manifest's git SHA, so
"what was promised" and "what was measured" are both auditable.

## 1. Sanity-check the registry (offline, seconds)

```bash
uv sync && uv run pytest -q                       # full deterministic suite
uv run python scripts/validate_draft.py --all     # every draft: schema + kernel + SQL
uv run python -m scripts.validate_pr registry/chainsafe.yaml   # gate check, any manifest
```

## 2. Run a review

Offline (fixture-backed team — the demo path, no network or credentials):

```bash
uv run fpm review chainsafe --manifest tests/fixtures/chainsafe.yaml --store /tmp/fpm_demo_store --dev-auto-approve
```

Live (real fetches through OSO, real model recommendation, interactive adjudication):

```bash
export OSO_API_KEY=...   # org-scoped key
uv run fpm review chainsafe --live --live-oso \
    --oso-org 35c17c26-4aa8-47ba-ba75-be8fe1e3718c --store .fpm_store
```

Each function prints `outcome → recommendation → adjudicated verdict`. You are the
adjudicator: the model's output is advisory (`a` approve / `revise` / `reject` /
`defer`). `--dev-auto-approve` exists for development only and says so loudly.

Outcome vocabulary: `pass` / `fail` / **`indeterminate`** (the source could not produce
a defensible number — never silently coerced to pass or fail).

## 3. Land verdicts to the warehouse

```bash
uv run fpm land --store .fpm_store --oso-org <org-uuid>
```

Lands two static-model tables (defaults):
- `filpgf_sla_verdicts` — public: facts, provenance, the advisory narrative.
- `filpgf_sla_verdicts_private` — org-scoped superset: + adjudication note, approver.

Query them like any OSO table:

```sql
SELECT team, function_id, metric, observed_value, sla_outcome, adjudicated_status
FROM filecoin.filpgf_sla_verdicts.filpgf_sla_verdicts
ORDER BY team, function_id;
```

## 4. Reviewing a manifest PR

1. Read the **static-gate job summary**: validation problems, and the goalpost report —
   `MATERIAL`/`loosened` lines are the ones that need committee eyes.
2. If the entry looks right, apply the **`dry-run-ok` label**: the live dry-run
   provisions the source in OSO, fetches once, posts the observed value, and cleans up.
   A FAILED run blocks merge — this is what catches "works on my machine" sources.
3. Host additions to `registry/_allowlist.txt` ride in the same PR — approving the PR
   approves the egress.
4. CODEOWNERS enforces that the team's own maintainers sign off on their file.

## 4b. Keep the time series accruing

Verdicts are snapshots; the dashboard's per-function history comes from the append-only
observations table (`filecoin.filpgf_sla_observations`). After landing, append the
run's readings and re-upload:

```bash
uv run python scripts/observations.py append --store .fpm_store
uv run python scripts/observations.py upload --oso-org <org-uuid>
```

`scripts/observations.py backfill` reconstructs history where a source's own data
carries it (DefiLlama daily TVL, Blockscout daily indexing charts, GitHub
release/commit event history, snapshot-archive listings, status-page incidents) —
every backfilled row is labelled with its method. `data/observations.csv` is the
git-tracked record.

## 5. Automate the reporting loop

The cadence loop is: review → land → append observations → dashboard reads the tables.

**The canonical full run is one command** — `scripts/run_full_review.sh`. It reviews every
registry team, lands the verdicts, and appends + uploads observations, in a fixed team order
with fixed flags, so an agent can run it identically every time:

```bash
export OSO_API_KEY=<org-scoped key>
scripts/run_full_review.sh                       # all defaults: fake synth, today's date, .fpm_store
scripts/run_full_review.sh --synth live          # real SDK advisory narratives (adds model variance)
scripts/run_full_review.sh --oso-org <uuid> --store /tmp/run --as-of 2026-07-16
```

What is and isn't deterministic:
- **Deterministic** — the *invocation*: same teams, same order, same flags every run.
- **Not deterministic (by design)** — the *results*: live readings change run-to-run; GitHub's
  60/hr unauth rate limit makes some GitHub-sourced functions read `indeterminate`
  non-deterministically (durable fix: a committee token via a source `auth.secret_ref`);
  `--synth live` narratives are model-generated.
- **No human in the loop** — the wrapper passes `--dev-auto-approve`, so every recommendation
  is auto-approved. That refreshes the dashboard/warehouse but is **not** a human-adjudicated
  funding decision — for that, review teams individually (§2) and adjudicate each call.

The production target (recorded decision) is a `ScheduledIngestionSink` where OSO pulls
verdict JSON on its own schedule, replacing the push in step 3.

```bash
scripts/demo_reviewer_flow.sh          # offline end-to-end demo of this whole guide
```

The dashboard (`dashboards/propgf-kernel-health.py`) renders the kernel taxonomy with
live SLA status per function, the Batch-3 funding slate, and per-function source
history:

```bash
uv sync --extra dashboards
export OSO_API_KEY=...
uv run marimo run dashboards/propgf-kernel-health.py
```

## Trust properties worth knowing

- **Evidence, not labels**: every reading carries an evidence bundle hash; citations
  bind to the hash, not to a URL that can change under you.
- **Manipulation detectors** run deterministically (indicators, not determinations) and
  ride with the recommendation.
- **Goalpost tracking**: SLA edits are diffed field-by-field and classified
  (material / new / trivial, tightened / loosened) — visible in every PR.
- **`indeterminate` is first-class**: a broken source is a fact to adjudicate, not a
  pass, not a fail.
