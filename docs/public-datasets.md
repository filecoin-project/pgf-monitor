# The public datasets

**Read the mart, not the landing tables.** Everything a consumer needs is in
`filecoin.filpgf_public.*` — the same UDM mart the rest of the Filecoin warehouse publishes
through, granted public read and queryable through the OSO API with any API key. Its SQL lives in
`insights-private/projects/filecoin/models/`; this repo publishes the raw tables it is built from.

**Two tables, on purpose.**

| table | one row per | rows |
|---|---|---|
| `filecoin.filpgf_public.kernel_timeseries_sla_by_project` | reading: day × team × function × metric | 673 |
| `filecoin.filpgf_public.kernel_functions` | kernel function in the inventory | 31 |

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
FROM filecoin.filpgf_public.kernel_timeseries_sla_by_project
WHERE grant_ref = 'APP-P706QNLF-NLQPG5'
ORDER BY metric_name, sample_date
```

`sample_date` is a real DATE in the mart (`WHERE sample_date = DATE '2026-08-19'`). In the raw
landing tables `observed_at` is a **varchar** `YYYY-MM-DD` instead — compare it to `'2026-08-19'`,
and `CAST(observed_at AS DATE)` if you need date arithmetic.

## What each column is for

On every row of `kernel_timeseries_sla_by_project`:

- **`grant_ref`** — the Karma application id (`APP-…`) of the grant that PAYS for this metric. This
  is the key to use when rendering against a grant, and it is not the same thing as the team: one
  recipient can hold two grants, and `team` cannot tell them apart. Empty on the one entry no grant
  pays for (a cross-check we run at our own expense).
- **`oso_project_slug`** — the OSO project slug of the party receiving payment. Carried as a plain
  column, deliberately **not** as a foreign key into `filpgf_public.projects`: a handful of these
  projects are not in that table, and an inner join would silently drop them rather than showing an
  uncovered project.
- **`kernel_id`** — the one kernel function this metric evidences. `non-kernel` means the metric is
  real but evidences nothing the inventory names; it is published as itself so it can't be mistaken
  for a missing value.
- **`state`** — `adopted` (in `registry/`, so a team is held to it today) or `draft` (modelled, not
  yet committed to). A metric can appear twice, once per state, which is how a team proposes its
  next version. **Filter on `state = 'adopted'` unless you specifically want the pipeline.**
- **`origin`** — who authored the entry: `oso`, `karma` (harvested from the team's application) or
  `external-pr`.
- **`source_host`** — the host the reading is fetched from, or `fixture` for a placeholder awaiting
  a real feed; `is_fixture` says the same thing as a boolean. A `fixture` row is not yet a live
  measurement.
- **`kernel_id_resolves`** — false when `kernel_id` names nothing in the inventory. Distinguishes
  "deliberately outside the taxonomy" (`non-kernel`) from "points at a function that no longer
  exists", so a null `kernel_function` is never ambiguous.
- **`repos`** — space-separated `owner/name`, lowercase, empty when the work is measured through an
  endpoint rather than a repository.

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
