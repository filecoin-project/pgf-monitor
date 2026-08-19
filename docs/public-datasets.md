# The public datasets

Four tables in the OSO warehouse, all granted public read, all queryable through the OSO API with
any API key. Together they are everything needed to rebuild
`dashboards/propgf-kernel-health.py` — metrics by team, by project, by grant, by kernel function —
without access to this repository.

| table | one row per | rows |
|---|---|---|
| `filecoin.filpgf_kernel_functions.filpgf_kernel_functions` | kernel function in the inventory | 31 |
| `filecoin.filpgf_kernel_metrics.filpgf_kernel_metrics` | SLA entry (adopted or draft) | 57 |
| `filecoin.filpgf_sla_observations.filpgf_sla_observations` | (day, team, function, metric) reading | ~2.5k |
| `filecoin.filpgf_sla_thresholds.filpgf_sla_thresholds` | (day, team, function, metric) commitment | ~1.4k |

The first two are regenerated from `registry/` and republished by the nightly
(`.github/workflows/observe.yml`, 06:17 UTC), the same run that appends the day's readings. All four
are full-table republishes: they are replaced, not appended to, so a query never sees a half-written
table.

## The join

Everything hangs off `(team, function_id, metric)`. That triple is the identity of a monitored
commitment, and it is stable — `team` is the registry filename stem, `function_id` is chosen by the
team, and neither is renamed in place (renaming one orphans its history, so we don't).

```sql
SELECT m.grant_ref,
       m.team,
       m.oso_project_slug,
       m.kernel_id,
       k.function        AS kernel_function,
       k.tier,
       k.category,
       m.metric,
       m.sla_statement,
       o.observed_at,
       o.observed_value
FROM filecoin.filpgf_kernel_metrics.filpgf_kernel_metrics m
JOIN filecoin.filpgf_kernel_functions.filpgf_kernel_functions k
     ON k.kernel_id = m.kernel_id
JOIN filecoin.filpgf_sla_observations.filpgf_sla_observations o
     ON o.team = m.team
    AND o.function_id = m.function_id
    AND o.metric = m.metric
WHERE m.state = 'adopted'
ORDER BY m.team, m.metric, o.observed_at
```

Note `observed_at` is a **varchar** `YYYY-MM-DD`, not a date — compare it to `'2026-08-19'`, and
`CAST(o.observed_at AS DATE)` if you need date arithmetic.

## What each column is for

`filpgf_kernel_metrics`:

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
  a real feed. A `fixture` row is not yet a live measurement.
- **`repos`** — space-separated `owner/name`, lowercase, empty when the work is measured through an
  endpoint rather than a repository.

`filpgf_kernel_functions` carries the inventory **including functions nothing measures yet**. That
is the point: coverage computed against only the covered functions always reads 100%. Left-join from
this table to get an honest denominator.

```sql
SELECT k.tier, k.function, count(m.metric) AS metrics
FROM filecoin.filpgf_kernel_functions.filpgf_kernel_functions k
LEFT JOIN filecoin.filpgf_kernel_metrics.filpgf_kernel_metrics m
       ON m.kernel_id = k.kernel_id AND m.state = 'adopted'
GROUP BY k.tier, k.function
ORDER BY metrics
```

## Compliance is not a column, on purpose

No table stores pass/fail. `filpgf_sla_thresholds` records the bar **as it stood on each day**, and
the outcome is derived at render time by joining it to the reading for the same day. That way
correcting a threshold fixes history, instead of leaving old rows judged against a number nobody
agreed to. Many metrics are measured and deliberately **not** scored: no bar has been agreed, so
`threshold_op` is null and nothing is asserted about compliance.

If you need the outcome, derive it with the same rule the dashboard uses:

```sql
CASE
  WHEN o.observed_value IS NULL   THEN 'indeterminate'  -- no defensible number this day
  WHEN t.threshold_op  IS NULL    THEN 'unscored'       -- measured, but no agreed bar
  WHEN t.threshold_op = '>=' THEN IF(o.observed_value >= t.threshold_value, 'pass', 'fail')
  WHEN t.threshold_op = '<=' THEN IF(o.observed_value <= t.threshold_value, 'pass', 'fail')
  WHEN t.threshold_op = '>'  THEN IF(o.observed_value >  t.threshold_value, 'pass', 'fail')
  WHEN t.threshold_op = '<'  THEN IF(o.observed_value <  t.threshold_value, 'pass', 'fail')
  WHEN t.threshold_op = '==' THEN IF(o.observed_value =  t.threshold_value, 'pass', 'fail')
  ELSE 'unscored'
END AS sla_outcome
```

Joined on `(observed_at, team, function_id, metric)` with a LEFT JOIN — an inner join drops exactly
the unscored metrics, which is most of them.

`indeterminate` and `unscored` are different failures and must not be collapsed: the first is ours
(we could not get a defensible number that day), the second is the absence of an agreed bar. Neither
is a breach, and neither should render as one.

## Regenerating

```bash
uv run python -m scripts.exports write                       # CSVs from registry/
uv run python -m scripts.exports upload --oso-org <uuid>     # regenerate, then republish both
```

`data/kernel_functions.csv` and `data/kernel_metrics.csv` are derived — never hand-edit them.
`tests/test_exports.py` fails when the committed copies disagree with `registry/`, so a manifest
change that forgets to regenerate cannot merge.
