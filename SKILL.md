---
name: filecoin-kernel-monitor
description: Answer questions about the Filecoin kernel and what each ProPGF-funded team committed to monitor — from public raw URLs, without cloning the repo. Use for "what did team X promise", "who maintains kernel function Y", "is it currently green", "how much ProPGF funding is attached".
---

# Filecoin Kernel Monitor — read-only agent skill

The [Filecoin kernel](https://www.oso.xyz/filecoin/propgf-kernel-health) is the set of
functions the network cannot operate without. Each ProPGF-funded team declares, in a public
manifest, which kernel functions it maintains and how to check each one. A pipeline fetches
each source, evaluates it, and publishes the result.

```
FUNCTION → SLA → SOURCE → READING → EVALUATION → RECOMMENDATION → VERDICT
        (the repo: what was promised)  (the pipeline: what was measured)  (a human: the call)
```

Keep those halves apart. A manifest tells you what a team **promised**. Only the pipeline
tells you what was **measured**. Never infer one from the other.

This skill is read-only. To *author* a manifest you need a clone and a pull request — see
`CLAUDE.md` in the repo.

## Fetchable artifacts

```
BASE=https://raw.githubusercontent.com/filecoin-project/pgf-monitor/main
```

| fetch | gives you | freshness |
|---|---|---|
| `$BASE/registry/_kernel.yaml` | the kernel taxonomy: every catalogued function, its tier and its `value` (why it matters) | changes by reviewed PR |
| `$BASE/registry/<team>.yaml` | one team's commitments — see "Reading a manifest" below | changes by reviewed PR |
| `$BASE/docs/kernel-coverage.md` | auto-generated matrix: every kernel function and the metrics monitoring it, naming every team | regenerated from the registry |
| `$BASE/badges.json` | headline counts: kernel functions, monitored metrics, teams, coverage | regenerated from the registry |
| `$BASE/dashboards/data/kernel_fallback.json` | last published verdicts, the funding slate with `committed_usd`, and historical observations | **a dated snapshot, not live** |

## Finding the teams

Raw URLs cannot list a directory, so there is no way to enumerate `registry/*.yaml` directly.
Two options:

1. Fetch `$BASE/docs/kernel-coverage.md` — it names every team in its tables, alongside the
   kernel functions they cover. Best starting point for almost any question.
2. Ask the GitHub API:
   `https://api.github.com/repos/filecoin-project/pgf-monitor/contents/registry`

Files beginning with `_` are shared infrastructure, not teams. `registry/drafts/<team>.yaml`
holds proposals that have not been adopted yet.

## Reading a manifest

Each entry in a team's `functions[]` list is one commitment (abridged — see a real manifest
for the full shape):

```yaml
- function_id: mainnet-block-explorer      # stable id for this commitment
  origin: external-pr                      # who proposed it: oso | karma | external-pr
  tier: essential                          # ┐
  category: 'UX/DX'                        # ├─ together these locate the kernel slot;
  sub_category: 'Explorers and Tooling'    # ┘  they match registry/_kernel.yaml exactly
  sla:
    statement: "Explorer keeps pace with the chain: largest gap between indexed tipsets <= 90s"
    metric: explorer_max_tipset_gap_seconds
    threshold: { op: "<=", value: 90 }     # the actual promise
    cadence: daily                         # how often it is checked
  source:
    kind: http-json
    base_url: "https://filfox.info"        # must be in registry/_allowlist.txt
    query: "/api/v1/tipset/recent"
  transform:
    sql: "SELECT MAX(g) FROM ..."          # how the reading is computed
```

- `(tier, category, sub_category)` → which kernel function this monitors. Cross-reference
  `_kernel.yaml` for that function's `value` — why the network needs it.
- `sla.threshold` → the commitment. `sla.statement` → it in prose.
- `source.extract` **or** the sibling `transform:` block (exactly one) → how the number is derived.
- `kernel_function` → present when several kernel functions share one taxonomy slot; it names
  the specific one.

## Recipes

**What did team X commit to?** Fetch `$BASE/registry/<team>.yaml`. For each `functions[]`
entry report `sla.statement`, `sla.metric`, `sla.threshold`, `sla.cadence`, and the source host.

**Who covers kernel function Y?** Fetch `$BASE/docs/kernel-coverage.md` and find Y's heading.
Its table lists every team, metric, source host, and whether the entry is adopted or a draft.

**Is it currently green?** Fetch `$BASE/dashboards/data/kernel_fallback.json` and look in
`verdicts` for `{team, function_id, metric, sla_outcome, observed_value, threshold_op,
threshold_value}`. State the snapshot's age — `max(observations[].observed_at)`, since
`verdicts` entries carry no timestamp of their own — and link the
[live dashboard](https://www.oso.xyz/filecoin/propgf-kernel-health) for current status.

**How much ProPGF funding is attached?** Same file, `slate` array: `team_name`,
`committed_usd`, `functions`.

## Honesty rules

These exist because the registry is a governance artifact — overstating it misleads a
funding decision.

- `kernel_fallback.json` is a **snapshot** committed for offline dashboard use, not a live
  feed. Always give its age — derive it from `max(observations[].observed_at)`; `verdicts`
  entries carry no timestamp of their own — and defer to the live dashboard.
- A threshold marked `PLACEHOLDER`, **or** any `# THRESHOLD … (placeholder, confirm with
  team)` comment above it, or a `@TODO-github-handle` maintainer, means **the team has not
  confirmed it yet**. Do not report these as commitments.
- A `fixture` source is a stand-in awaiting a real feed, not a measurement.
- Some metrics are deliberately *maintenance* proxies (commit or release recency), not
  liveness signals. Manifest comments say so. Do not upgrade a proxy into a claim about the
  service running.
- Thresholds are human commitments arrived at by negotiation. Never invent, tighten, or
  loosen one.
- Prefer quoting `sla.statement` over paraphrasing it.
