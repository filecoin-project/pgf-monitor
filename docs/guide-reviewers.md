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
a defensible number — never silently coerced to pass or fail) / **`unscored`** (a value
*was* measured, but no threshold is on file for that day — a manifest with no
`sla.threshold`, or a reading that predates the thresholds series). Don't conflate the
two: `indeterminate` is a fact-finding failure, `unscored` is the absence of an agreed
bar to judge a perfectly good reading against.

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
   `MATERIAL`/`loosened` lines are the ones that need committee eyes. A threshold
   appearing or disappearing classifies as `MATERIAL` too (`tightened` for appearing,
   `loosened` for disappearing), same as any other goalpost move.
   A goalpost move never *fails* the job: material changes are reported and the gate still
   exits 0, because withdrawing or loosening a commitment is a governance decision for the
   committee, not a rule violation for CI to block. The gate goes red only on things no
   committee vote can make safe — schema errors, a kernel slot that doesn't match, a source
   whose config won't translate, transform SQL outside the single-SELECT guard, or a host that
   isn't on the allowlist.
2. If the entry looks right, apply the **`dry-run-ok` label**: the live dry-run
   provisions the source in OSO, fetches once, posts the observed value, and cleans up.
   A FAILED run blocks merge — this is what catches "works on my machine" sources.
3. Host additions to `registry/_allowlist.txt` must land in an **earlier** PR than the
   manifest that uses them. Both `validate.yml` and `dry-run.yml` read the allowlist from the
   BASE branch, never the PR head, so a host added in the same PR is not yet trusted when its
   metric is checked: the static gate reports `base_url host not on allowlist` and the live
   dry-run cannot prove the metric at all. Approve the host PR first (approving it approves the
   egress), then the metric PR.
4. CODEOWNERS enforces that the team's own maintainers sign off on their file.

## 4b. Keep the time series accruing

Verdicts are snapshots; the dashboard's per-function history comes from two append-only
tables that the dashboard joins at render time: `data/observations.csv` (what was
measured — `filecoin.filpgf_sla_observations`) and `data/thresholds.csv` (the bar as it
stood that day — `filecoin.filpgf_sla_thresholds`). Neither stores an outcome; the join
key is `(observed_at, team, function_id, metric)`, and pass/fail/unscored/indeterminate
is derived at render. That means correcting a threshold fixes history — old readings get
re-judged against the corrected bar instead of staying wrong forever. The thresholds
series starts 2026-08-16 with no backfill, so anything measured before that date renders
`unscored`: we decline to assert today's threshold over readings we didn't have a bar
for at the time.

**This is automatic now.** `.github/workflows/observe.yml` runs nightly at 06:17 UTC, measures
every adopted metric, and commits the readings to both `data/observations.csv` and
`data/thresholds.csv`. It runs `fpm observe` — the deterministic half of the pipeline, fetch and
evaluate only. No model, no adjudication: a verdict stays a human act, and nothing unattended
ever writes one. A red run in the Actions tab means the readings did not land that night; re-run
it by hand from the same tab (`Run workflow`), optionally with an `as_of` date to fill a specific
gap.

To take a reading yourself — after a review, or to check a source before merging:

```bash
uv run fpm observe                                   # every adopted manifest, today
uv run fpm observe chainsafe --dry-run               # one team, write nothing
uv run fpm observe --live-oso --oso-org <org-uuid>   # fetch for real (needs OSO_API_KEY)
```

`fpm observe` is idempotent per day: re-running it replaces that day's rows rather than
appending duplicates, so a re-run after fixing a source leaves the good reading in place.

After landing verdicts, re-publish the tables and the notebook so the dashboard sees the
new rows. The order matters and must not be inverted:

1. `scripts/observations.py upload-thresholds --oso-org <org-uuid>` — creates/refreshes
   `filpgf_sla_thresholds`.
2. Publish the notebook — safe to do against the OLD (wider) observations table, because
   the new query names only columns that exist in both the old and narrowed schemas.
3. `scripts/observations.py upload --oso-org <org-uuid>` — republishes
   `filpgf_sla_observations`, narrowed to the columns the notebook's committed query
   expects.

Inverting this order produces a window where the dashboard's `obs_data` cell hits its bare
`except Exception` fallback (which has no `observations` entry), so every chart and uptime
strip silently disappears: thresholds must exist, and the notebook must already be
querying the narrowed shape, before the narrowed observations table replaces the old one.

```bash
uv run python scripts/observations.py upload-thresholds --oso-org <org-uuid>
# publish the notebook here
uv run python scripts/observations.py upload --oso-org <org-uuid>
```

`scripts/observations.py backfill` reconstructs history where a source's own data
carries it (DefiLlama daily TVL, Blockscout daily indexing charts, GitHub
release/commit event history, snapshot-archive listings, status-page incidents) —
every backfilled row is labeled with its method. `data/observations.csv` and
`data/thresholds.csv` are the git-tracked records; never hand-edit either.

## 5. Automate the reporting loop

The cadence loop is: review → append observations → dashboard reads the tables. Landing
verdicts is a separate, human step (§2) and deliberately not part of the loop.

**The canonical full run is one command** — `scripts/run_full_review.sh`. It reviews every
registry team and appends + uploads the observations and thresholds series, in a fixed team
order with fixed flags, so an agent can run it identically every time. **It lands no
verdicts**: it passes `--dev-auto-approve`, and `fpm land` refuses a batch approved that way.

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
- **No human in the loop, and therefore nothing landed** — the wrapper passes
  `--dev-auto-approve`, so every recommendation in the store is stamped `approver="dev-auto"`.
  That refreshes measurement (observations, thresholds), which carries no judgment. It is
  **not** a funding decision, and `fpm land` now raises `UnadjudicatedVerdictError` on such a
  batch rather than publishing it. To land verdicts, review teams individually (§2) and
  adjudicate each call.
- **A partial run exits non-zero** — if any team's review failed, the uploaded series is
  missing that team, so the script fails rather than reporting a clean run.

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
  (material / new / trivial, tightened / loosened) — visible in every PR. A threshold
  appearing or disappearing is diffed the same way.
- **`indeterminate` is first-class**: a broken source is a fact to adjudicate, not a
  pass, not a fail. **`unscored`** is a different fact: the reading is fine, there is
  just no agreed bar to judge it against yet.
