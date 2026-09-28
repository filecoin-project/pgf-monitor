---
name: query-gtm-pipeline
description: Use when evaluating a Filecoin pod, or answering any question about the pods' go-to-market sales pipeline — how big FilOne's open book is, how it splits by stage, how many FOC partnerships are open, won, lost or dormant, how fresh the pipeline data is. Queries the one public table, `filecoin.filpgf_public.gtm_pipeline_by_stage`, with any OSO API key. Triggers on "GTM pipeline", "sales pipeline", "pipeline by stage", "FilOne book", "FOC partnerships", "pod funnel", "weighted pipeline". For kernel SLA readings use `docs/public-datasets.md` instead.
---

# Query the pods' GTM pipeline

The Filecoin pods' sales pipelines are published as **one public table**:

```
filecoin.filpgf_public.gtm_pipeline_by_stage
```

It holds one row per pod × stage, built daily from the pods' own CRM data. Everyone reads this
same table: the community, filpgf.io, and sims evaluating a pod. There's no richer version to
ask for, so don't go looking for one. Deal-level and partner-level records are private by
design, and the query will be denied.

## Connecting

Any OSO API key reads it (create one at oso.xyz). The warehouse speaks **Trino SQL**.

- **Python:** `uv add pyoso`, set `OSO_API_KEY`, then
  `pyoso.Client().to_pandas("SELECT ... FROM filecoin.filpgf_public.gtm_pipeline_by_stage")`.
- **MCP:** the OSO MCP server at `https://mcp.oso.xyz/mcp` (Bearer token = your API key)
  exposes a SQL tool that takes the same query.

## The two pods

| `pod_slug` | `pod_display_name` | Source | Unit | Measures |
|---|---|---|---|---|
| `web2` | Web2 Object Storage | the FilOne channel & enterprise book (HubSpot-derived, refreshed daily) | `deal` | count, amount, weighted amount, PB |
| `foc` | Filecoin Onchain Cloud | the FOC partnership tracker (a hand-maintained sheet) | `partnership` | **count only** |

The pod slugs match `filecoin.filpgf_public.timeseries_metrics_by_pod` and `key_metrics_by_pod`,
so you can join pipeline to the pods' funding and activity metrics.

## Columns

| Column | Meaning |
|---|---|
| `snapshot_date` | the day the pipeline was read |
| `pod_slug`, `pod_display_name` | which pod |
| `entity_kind` | `deal` or `partnership` |
| `stage` | the pod's own stage name, e.g. Prospect / Discovery for web2, In Progress / Existing Partner for foc |
| `stage_order` | position in that pod's ladder; **null on the folded row** |
| `stage_kind` | `open`, `won`, `lost` or `dormant` |
| `is_folded` | true for the "Other open stages" row |
| `entity_count` | deals or partnerships in the row |
| `amount_usd` | web2 only: first-year contract value if every deal in the row closed, rounded to $0.1M |
| `weighted_usd` | web2 only: each deal's amount × its stage's win probability, summed, rounded to $0.1M |
| `pb`, `weighted_pb` | web2 only: storage capacity in PB, rounded to 1 PB |
| `source_updated_at` | web2 only: when the CRM last synced |

## Read these before you draw a conclusion

1. **It's a snapshot, not a time series.** The table holds only the latest reading per pod.
   Nothing here supports conversion rates, stage velocity or "the pipeline grew" claims. If you
   need a trend, say the data can't show one.
2. **The pods can be on different dates.** Check `snapshot_date` per pod every time. The FOC
   tracker is updated by hand and can be weeks behind web2, so an FOC count is only as current
   as its date.
3. **Never compare `stage_order` across pods.** web2's ladder runs Prospect → Propose and has no
   won stage at all; foc's runs Inbound → Existing Partner (won), with Stale meaning dormant, not
   progress. Compare pods with **`stage_kind` and counts only**.
4. **Never add money across pods.** foc's measures are null because the tracker records no deal
   sizes or probabilities. That means unknown, not zero.
5. **Small stages are folded.** Any web2 stage with fewer than 3 deals is merged into one "Other
   open stages" row, and that row is dropped if it still has fewer than 3. That rule exists so
   no single deal's value is published. Don't try to back out an individual deal from
   differences between rows or days.
6. **Figures are rounded.** Rounding is $0.1M per row, so sums can differ from the exact book by
   up to $50k per row. Quote them as approximate ("about $X M").
7. **Open book only.** Lost web2 deals are excluded. `amount_usd` is potential value, not
   revenue: there's no closed-won stage in the feed, so nothing here shows signed contracts.

## Queries

**Freshness first**, one row per pod:

```sql
SELECT
  pod_slug,
  MAX(snapshot_date) AS snapshot_date,
  MAX(source_updated_at) AS source_updated_at
FROM filecoin.filpgf_public.gtm_pipeline_by_stage
GROUP BY pod_slug
```

**Each pod's funnel:**

```sql
SELECT
  g.pod_slug,
  g.stage,
  g.stage_kind,
  g.is_folded,
  g.entity_count,
  g.amount_usd,
  g.weighted_usd,
  g.pb
FROM filecoin.filpgf_public.gtm_pipeline_by_stage AS g
ORDER BY g.pod_slug, g.stage_order NULLS LAST
```

**web2's open book in one row.** The weighted share is the expected fraction of the book that
closes:

```sql
SELECT
  SUM(entity_count) AS deals,
  SUM(amount_usd) AS open_book_usd,
  SUM(weighted_usd) AS weighted_usd,
  SUM(weighted_usd) / SUM(amount_usd) AS weighted_share,
  SUM(pb) AS pb
FROM filecoin.filpgf_public.gtm_pipeline_by_stage
WHERE pod_slug = 'web2'
```

**The only fair cross-pod comparison**, counts by `stage_kind`:

```sql
SELECT
  stage_kind,
  pod_slug,
  SUM(entity_count) AS entities
FROM filecoin.filpgf_public.gtm_pipeline_by_stage
GROUP BY stage_kind, pod_slug
ORDER BY stage_kind, pod_slug
```

## Writing it up

- Lead with the snapshot date of each pod you cite.
- For web2, the useful figures are open book, weighted pipeline and deal count by stage. For foc,
  the useful figures are counts by `stage_kind`, and you should say plainly that it carries no
  value figures.
- Don't speculate about which companies are in the pipeline, and don't treat the absence of
  names as missing data: it's the publication rule.
