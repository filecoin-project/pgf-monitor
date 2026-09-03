# The public datasets

**Read the mart, not the landing tables.** Everything a consumer needs is in
`filecoin.filpgf_public.*` — the same UDM mart the rest of the Filecoin warehouse publishes
through, granted public read and queryable through the OSO API with any API key. Its SQL lives in
`insights-private/projects/filecoin/models/`; this repo publishes the raw tables it is built from.

**Two tables, on purpose.**

| table | one row per | size |
|---|---|---|
| `filecoin.filpgf_public.kernel_timeseries_metrics_by_project` | reading: day × team × function × metric | ~40 rows **per day**; 875 rows **cumulative** across all history as of 2026-08-25 |
| `filecoin.filpgf_public.kernel_functions` | kernel function in the inventory | 31, of which 17 have a reporter |

Those two numbers measure different things and must never be compared with each other. The
per-day count is the health signal — if it stops matching the number of live commitments, something
upstream has stalled. The cumulative total keeps rising even during a stall (early history is
sparse: 875 rows spread over 378 distinct `sample_date`s), so it can never detect one.

**Reference implementation.** [`propgf-kernel-health-live`](https://www.oso.xyz/filecoin/propgf-kernel-health-live)
is a working consumer of exactly these two tables and nothing else — source in this repo at
`dashboards/propgf-kernel-public.py`. It embeds no data and queries live, so any OSO API key
reproduces every number on it. Read it as the worked example of this contract. Note that the
similarly-named `propgf-kernel-health` is the *internal* committee view and reads private models;
it is not a consumer of this contract.

Every fact about a reading rides on the reading — what it is evidence for, who is paid for it, and
**the bar as it stood that day** — so thresholds and the metric registry need no tables of their
own. `kernel_functions` stays because the 14 kernel functions nothing measures yet have no readings
to ride on, and a coverage number computed without them always reads 100%.

Neither a threshold nor a verdict can be *derived* from a reading: a bar is a promise and a verdict
is a human judgment. The bar is joined in upstream, so it arrives on the row. Adjudicated verdicts
are not in the mart at all — they live in `filecoin.filpgf_sla_verdicts.filpgf_sla_verdicts`.

The landing tables this repo republishes nightly — `filpgf_kernel_functions`,
`filpgf_kernel_metrics`, `filpgf_sla_observations` and `filpgf_sla_thresholds`, each
`filecoin.<name>.<name>` — are public too, but they are the mart's inputs: unjoined, and keyed only
on `(team, function_id, metric)`. Query them only if you are rebuilding the mart.

## The join

Everything hangs off `(team, function_id, metric)`. That triple is the identity of a monitored
commitment, and it is stable — `team` is the registry filename stem, `function_id` is chosen by the
team, and neither is renamed in place (renaming one orphans its history, so we don't). In the mart the join is
already done, bar included — you need the triple only to attach verdicts, or to line rows up
against the landing tables.

```sql
SELECT grant_ref, team, project_display_name, kernel_function, tier,
       metric_name, sample_date, amount
FROM filecoin.filpgf_public.kernel_timeseries_metrics_by_project
WHERE grant_ref = 'APP-P706QNLF-NLQPG5'
ORDER BY metric_name, sample_date
```

`sample_date` is a real DATE in the mart (`WHERE sample_date = DATE '2026-08-19'`). In the raw
landing tables `observed_at` is a **varchar** `YYYY-MM-DD` instead — compare it to `'2026-08-19'`,
and `CAST(observed_at AS DATE)` if you need date arithmetic.

## What each column is for

On every row of `kernel_timeseries_metrics_by_project`:

- **`grant_ref`** — the Karma application id (`APP-…`) of the grant that PAYS for this metric. This
  is the key to use when rendering against a grant, and it is not the same thing as the team: one
  recipient can hold two grants, and `team` cannot tell them apart. **`grant_ref IS NOT NULL` is
  the filter for "funded projects"** — it currently yields 14 grants, one per funded project.
  Empty on the one entry no grant pays for (a cross-check we run at our own expense); see
  `oso_project_slug = 'unfunded'` below.
- **`oso_project_slug`** — the OSO project slug of the party receiving payment. Carried as a plain
  column, deliberately **not** as a foreign key into `filpgf_public.projects`: a handful of these
  projects are not in that table, and an inner join would silently drop them rather than showing an
  uncovered project.

  The literal **`unfunded`** is a SENTINEL, not a missing mapping, and it is the honest answer
  rather than a gap to be filled. It marks a reading nobody is paid for: today one row, the
  `mainnet-block-explorer` freshness check measured from **Filfox**, an explorer no ProPGF grantee
  operates. Both the FilOz and Plumbline Appendix 1 §4 tables record Filfox as "third party,
  ProPGF funded? N". It carries no `grant_ref` and a null `project_display_name`.

  It sits in the Blockscout team file because `team` is our registry filename stem — where a
  commitment is tracked — and NOT a funding attribution; `oso_project_slug` is the attribution.
  Attributing this reading to Blockscout would assert they are funded to keep a third party's
  index current. Blockscout's own funded explorer metrics are in the same file under slug
  `blockscout` with `grant_ref APP-J8CF3XJY-CG03HL`, which is why the slug looks available.

  So a count of distinct `oso_project_slug` is 15 while the funded-project count is 14. Filter on
  `grant_ref IS NOT NULL` rather than excluding the string: a future third-party cross-check will
  also be null but may not reuse this value.
- **`karma_project_id`** / **`karma_project_slug`** — the Karma project the grant is attached to,
  resolved from `grant_ref`. The **id** (`0x…`) is the stable key and the one to join on; the
  **slug** is human-readable but MUTABLE — Karma derives it from the application title, so it
  changes on a rename and collisions take a numeric suffix (`filponto-1`). Both are null on the
  `unfunded` cross-check. Note the Karma project is not the same entity as `oso_project_slug`: it
  is the applicant's project on Karma (e.g. grant `APP-HDYJESMD-2WLL00` pays OSO slug `filozone`
  but its Karma project is `curio`), so this is the key for reconciling against Karma, not for
  funding attribution.
- **`kernel_id`** — the one kernel function this metric evidences. `non-kernel` means the metric is
  real but evidences nothing the inventory names; it is published as itself so it can't be mistaken
  for a missing value.
- **`project_display_name`** — the payee's display name where OSSD has one, null otherwise. Render
  this rather than `team`; `team` is our filename stem, not what anyone calls themselves.
- **`method`** — how that day's reading was taken: `nightly` (the unattended run), `live-review`
  (taken during a review), or `backfill:<host>` where the source's own history was reconstructed
  after the fact. A day can carry more than one row for one commitment when a backfill lands beside
  a nightly reading; they are different observations of the same day, not duplicates.

  **2026-08-22 and 2026-08-23 were OUR outage, not any source's.** OSO migrated the payload type
  of its run-request mutations and every fetch raised a bare 400, so 38 of 38 commitments recorded
  a null that night and the next. Those two dates should be excluded from any coverage or
  availability denominator you compute — charging a team for them measures us, not them. Our own
  public dashboard drops them outright. Two metric-days were later recovered as real readings
  under `backfill:api.github.com` and `backfill:api.geckoterminal.com`, because those sources keep
  their own history; the rest are point-in-time and gone for good.
- **`threshold_source`** — `signed-appendix` when the bar was read out of a signed appendix,
  `provisional` otherwise. Every row is `provisional` today, and every `threshold_op` is null.
- **`time_interval`** — always `daily`, for shape-compatibility with the sibling
  `timeseries_metrics_by_project`.

**Adopted only, and six columns are NOT here.** The mart is built through
`filecoin.metrics.metrics_filpgf_sla`, which joins `state = 'adopted'` — a draft is not a
commitment, so drafts never reach these tables at all. Their existence is visible only as
`kernel_functions.draft_metrics`. That also means **`state`, `origin`, `source_host`, `is_fixture`,
`kernel_id_resolves` and `repos` are not columns of this table**: they belong to
`filecoin.entities.registry_kernel_metrics`, one layer below, which is internal to the Filecoin org
and not public-read. An earlier version of this page listed them here and told you to filter on
`state`, which was doubly wrong — the column does not exist, and the filtering is already done. If
you need any of them, ask; do not write a query against them.

`kernel_functions` carries the inventory **including functions nothing measures yet**, with the
counts already computed. That is the point: coverage against only the covered functions always
reads 100%.

```sql
SELECT tier, kernel_function, adopted_metrics, adopted_teams
FROM filecoin.filpgf_public.kernel_functions
WHERE is_in_scope          -- irreplaceable + essential, the tiers ProPGF funds
ORDER BY adopted_metrics, kernel_function
```

## Compliance is not a column, on purpose

No table stores pass/fail. The bar rides on each reading **as it stood on that day**, and the
outcome is derived at render time from the two columns. That way correcting a threshold fixes
history — the mart rebuilds nightly against the corrected series — instead of leaving old rows
judged against a number nobody agreed to.

**As of 2026-08-20 nothing is scored at all.** Every bar has been withdrawn, in the registry and
across the whole history, because the agreements carrying them are not executed — a number in a
draft appendix is not yet a promise. So `threshold_op` is null on every row, every reading derives
as `unscored`, and the derivation below currently tells you only that. The numbers are not lost; they sit
in the maintainer-local facts files and come back, unchanged, when contracts are countersigned. The
derivation stays documented because it is what the table is for.

If you need the outcome, derive it with the same rule the dashboard uses:

```sql
CASE
  WHEN amount       IS NULL THEN 'indeterminate'  -- no defensible number that day
  WHEN threshold_op IS NULL THEN 'unscored'       -- measured, but no agreed bar
  WHEN threshold_op = '>=' THEN IF(amount >= threshold_value, 'pass', 'fail')
  WHEN threshold_op = '<=' THEN IF(amount <= threshold_value, 'pass', 'fail')
  WHEN threshold_op = '>'  THEN IF(amount >  threshold_value, 'pass', 'fail')
  WHEN threshold_op = '<'  THEN IF(amount <  threshold_value, 'pass', 'fail')
  WHEN threshold_op = '==' THEN IF(amount =  threshold_value, 'pass', 'fail')
  ELSE 'unscored'
END AS sla_outcome
```

No join needed: `threshold_op` and `threshold_value` are columns on the same row as `amount`, and
`threshold_source` says whether the number came from a signed appendix or is provisional.

`indeterminate` and `unscored` are different failures and must not be collapsed: the first is ours
(we could not get a defensible number that day), the second is the absence of an agreed bar. Neither
is a breach, and neither should render as one.

## Regenerating

This repo owns the landing tables:

```bash
uv run python -m scripts.exports write                       # CSVs from registry/
uv run python -m scripts.exports upload --oso-org <uuid>     # regenerate, then republish both
```

`data/kernel_functions.csv` and `data/kernel_metrics.csv` are derived — never hand-edit them.
`tests/test_exports.py` fails when the committed copies disagree with `registry/`, so a manifest
change that forgets to regenerate cannot merge.

The mart on top is `insights-private/projects/filecoin/models/` — four `staging__filpgf__*`
models, two `registry_kernel_*` entities, `metrics_filpgf_sla`, and the two `filpgf_public`
marts. Deploy with that repo's `scripts/deploy_models.py`, layer by layer in DAG order. Every
model runs `@daily` on its own, so a registry change reaches the mart within a day of the nightly
republish without anyone doing anything.
