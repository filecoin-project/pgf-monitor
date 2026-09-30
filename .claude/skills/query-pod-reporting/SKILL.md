---
name: query-pod-reporting
description: Use when evaluating a Filecoin Revenue Development pod (FOC, LDO, Fil One / web2), or answering any question about what a pod committed to, whether it delivered, how much it has been paid, or how its own reported KPIs are trending. Queries the public pod tables in `filecoin.filpgf_public` (pod_commitments, pod_funding, pod_review_metrics, pod_review_activity) with any OSO API key. Triggers on "pod commitments", "did the pod deliver", "pod funding", "paid to date", "pod KPIs", "business review metrics", "WBR", "evaluate FOC / LDO / Fil One". For the pods' sales pipelines use `query-gtm-pipeline`; for kernel SLA readings use `docs/public-datasets.md`.
---

# Query the pods' public reporting

Filecoin's Revenue Development track funds three **pods**, each with its own product and revenue
mandate. Everything published about how they're doing is in four public tables:

| Table | One row per | What it answers |
|---|---|---|
| `filecoin.filpgf_public.pod_commitments` | pod × commitment | What did the pod commit to, and where does each commitment stand? |
| `filecoin.filpgf_public.pod_funding` | pod | How much was committed, how much has been paid, what's the current roadmap tranche? |
| `filecoin.filpgf_public.pod_review_metrics` | pod × KPI × week | The KPIs each pod reports in its own biweekly business review |
| `filecoin.filpgf_public.pod_review_activity` | pod × review | How many items each review tracked and closed |

Everyone reads these same tables: the community, filpgf.io, and sims evaluating a pod. Nothing
richer is available. The pods' review documents, item text and owner names are private by
design, and a query for them will be denied.

## Connecting

Any OSO API key reads them (create one at oso.xyz). The warehouse speaks **Trino SQL**.

- **Python:** `uv add pyoso`, set `OSO_API_KEY`, then
  `pyoso.Client().to_pandas("SELECT ... FROM filecoin.filpgf_public.pod_commitments")`.
- **MCP:** the OSO MCP server at `https://mcp.oso.xyz/mcp` (Bearer token = your API key).

## The pods

| `pod_slug` | Name | Run by | What it does |
|---|---|---|---|
| `foc` | Filecoin Onchain Cloud | FilOz | developer-facing warm storage, verifiable retrieval, Filecoin Pay |
| `ldo` | Large Data Onboarding | FIDL | pooled SP capacity, paid retrievals, dataset onboarding |
| `web2` | Fil One (Web2 Object Storage) | Filecoin Foundation | S3-compatible storage for enterprise buyers |

`pod_slug` matches `timeseries_metrics_by_pod` / `key_metrics_by_pod` (funding and on-chain
activity) and `gtm_pipeline_by_stage` (sales pipeline), so all of them join.

## Columns worth knowing

**`pod_commitments`**:
- `goal_label` and `target_text`: the commitment.
- `status`: `done`, `done_early`, `done_late`, `on_track`, `at_risk`, `off_track` or `unconfirmed`.
- `is_delivered`: true for any `done*` status.
- `reviewed_on`: when the status was judged.
- `achieved_note_public`: a short public note on what landed.
- `note_status`: whether that note is `reviewed` by a person or still an `agent_draft`.

**`pod_funding`**:
- `committed_usd` and `paid_to_date_usd`.
- `paid_is_tracked`: whether the payment tracker covers the pod at all.
- `roadmap_label` / `roadmap_text`: the current tranche.
- `roadmap_amounts_redacted`: whether per-milestone prices were stripped.
- `karma_grant_ref`, and `as_of`.

**`pod_review_metrics`**: `metric_key` / `metric_label`, `week_ending`, `value_numeric`,
`target_numeric`, `extraction_method` (`regex` or `llm_targeted`).

**`pod_review_activity`**: `week_ending`, `tracked_items`, `resolved_items` and
`resolved_substantive_items` (items of 60+ characters, meaning real issues rather than legend
entries).

## Read these before you draw a conclusion

1. **Statuses are judgments with a date.** `pod_commitments.status` was set by reviewers on
   `reviewed_on`, not recomputed daily. Always cite the date. Check `note_status` before
   quoting `achieved_note_public`: an `agent_draft` note hasn't yet been confirmed by a person.
   A commitment with no public note shows it as NULL on purpose (`withheld_pending_review`).
2. **`paid_to_date_usd` understates.** It counts settled invoices on one payment tracker only.
   - Where `paid_is_tracked` is false (Fil One today), the value is **NULL, meaning unknown, not
     zero**.
   - FOC's first-half tranches were paid outside the tracker and aren't included.
   
   Never report a track-wide total from this column without saying it's a floor.
3. **There is no unit column, deliberately.** On some rows the source's unit described the
   *target*, not the value: LDO's `total_tib_onboarded` is in TiB while its target is in PiB.
   Dividing that value by its target gives about 155× instead of about 15%. **Only compare
   `value_numeric` with `target_numeric` when you know both are in the same unit.** Read the
   unit from `metric_label` and, if it's still unclear, say so.
4. **KPIs are self-reported and extracted from documents.** They come from each pod's own
   business review, read by regex or a targeted LLM pass. They're the pod's claim, not an
   independent measurement. Only 12 curated metric keys are published; there is no hidden longer
   list to ask for.
5. **Prefer `metric_label` over `metric_group`.** Some `metric_group` values carry stray text
   from the source document. Group KPIs by pod and `metric_key`.
6. **Review cadence differs by pod.** FOC and Fil One report roughly weekly and LDO about every
   other week, so the latest `week_ending` differs per pod. Always take the latest reading **per pod and per
   metric**, never a single global `MAX(week_ending)`.
7. **Money is committed and paid amounts only.** Payment schedules, tranche pricing and funding
   decisions aren't published, so don't infer them.

## Queries

**Where each pod stands on its commitments:**

```sql
SELECT
  pod_slug,
  COUNT(*) AS commitments,
  COUNT_IF(is_delivered) AS delivered,
  COUNT_IF(status IN ('at_risk', 'off_track')) AS at_risk_or_off_track,
  MAX(reviewed_on) AS reviewed_on
FROM filecoin.filpgf_public.pod_commitments
GROUP BY pod_slug
ORDER BY pod_slug
```

**Each commitment, with its public note only if a person has confirmed it:**

```sql
SELECT
  pod_slug,
  goal_order,
  goal_label,
  target_text,
  status_label,
  CASE WHEN note_status = 'reviewed' THEN achieved_note_public END AS note,
  reviewed_on
FROM filecoin.filpgf_public.pod_commitments
ORDER BY pod_slug, goal_order
```

**Funding, keeping unknown distinct from zero:**

```sql
SELECT
  pod_slug,
  pod_display_name,
  committed_usd,
  CASE WHEN paid_is_tracked THEN paid_to_date_usd END AS paid_to_date_usd,
  paid_is_tracked,
  as_of
FROM filecoin.filpgf_public.pod_funding
ORDER BY pod_slug
```

**The latest reading of every KPI, per pod:**

```sql
SELECT
  m.pod_slug,
  m.metric_label,
  m.week_ending,
  m.value_numeric,
  m.target_numeric
FROM filecoin.filpgf_public.pod_review_metrics AS m
JOIN (
  SELECT pod_slug, metric_key, MAX(week_ending) AS week_ending
  FROM filecoin.filpgf_public.pod_review_metrics
  GROUP BY pod_slug, metric_key
) AS l
  ON l.pod_slug = m.pod_slug
  AND l.metric_key = m.metric_key
  AND l.week_ending = m.week_ending
ORDER BY m.pod_slug, m.metric_label
```

**How actively each pod reviews and closes issues:**

```sql
SELECT
  pod_slug,
  COUNT(*) AS reviews,
  MIN(week_ending) AS first_review,
  MAX(week_ending) AS latest_review,
  SUM(resolved_substantive_items) AS resolved_substantive
FROM filecoin.filpgf_public.pod_review_activity
GROUP BY pod_slug
ORDER BY pod_slug
```

## Writing it up

- Lead with each pod's commitments: how many were delivered, how many are at risk, and the
  review date.
- Cite KPIs as the pod's own reported figures, with their `week_ending`.
- Present money as committed vs paid, and name any pod whose paid figure is unknown.
- Don't speculate about customers, partners or people behind the numbers. Their absence is the
  publication rule, not missing data.
