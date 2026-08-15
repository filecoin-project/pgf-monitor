# DUMMY APPLICATION — Lily (Sentinel chain ETL)

> **FICTIONAL. Not a real submission.** Written 2026-08-05 as an illustrative example of a
> kernel-track ProPGF application, using the field set of Karma application
> `APP-9PTCWEQL-HVKGV8` (FilPonto, Batch 3). The reference number, dates, dollar figures and
> targets are invented. The project facts (repo activity, release history, BigQuery dataset,
> open issues, NV28/NV29 timing) were probed live on 2026-08-05 and are real. No individual
> is named — a real submission would carry a real point of contact.
>
> Two fields marked **`NEW — proposed`** do not exist in the current form. Rationale at the end.

**Application info**

| | |
|---|---|
| Application ID | `APP-EXAMPLE-LILY01` (fabricated) |
| Program | Filecoin ProPGF Batch 4 |
| Status | Pending |
| Last submission | Nov 9, 2026 |
| Application details | 24 fields (22 current + 2 proposed) |
| Milestones | 2 |

---

## 1.1 Project Name

Lily (Sentinel chain ETL)

## Karma Profile

`<project UID>`

## 1.2 Project Github

https://github.com/filecoin-project/lily

## 1.3 Project Website

https://lily.starboard.ventures

## 1.4 Team Lead/Point of Contact

Lily maintainer, Starboard — Filecoin Slack (`@<handle>`) or Telegram (`@<handle>`)

## 1.5 Category

Core Infrastructure

### Contributing to Core Infrastructure?

Lily is the chain ETL every open Filecoin dataset sits on. It indexes and normalizes on-chain
state into the public `lily-data.lily` BigQuery dataset and the tables behind the Spacescope
API, so analysts, Pods, dashboards and SP tooling read normalized network data instead of
re-processing the chain.

## 1.6 Open Source Status

Fully Open Source

## 1.7 Kernel function(s) this work maintains — **`NEW — proposed`**

Selected verbatim from the Filecoin Kernel inventory. Primary first.

| # | Tier | Category | Sub-category | Function (verbatim) |
|---|---|---|---|---|
| 1 | Essential | Coordination & Incentives | Network data & monitoring | Chain ETL, indexing, normalization & parameter matching (BigQuery, Spacescope API) |
| 2 | Essential | Coordination & Incentives | Network data & monitoring | Aggregates Filecoin on/off-chain data into open, queryable datasets and dashboards |

Function 1 is the software and the pipeline: Lily itself, its actor shims and its schema.
Function 2 is the served surface: the public BigQuery dataset and the Spacescope tables loaded
from it. Both live in the same tier/category/sub-category slot, so naming the slot alone does
not identify the work — the function strings above do. We are **not** claiming the third entry
in that slot ("Chain ETL and indexing", currently unattributed); if the committee reads that as
the same function as #1, we would rather it were merged than split between us and someone else.

## 2.1 Project Summary

Lily is an instrumented Lotus node that extracts permanent chain state — actors, messages,
receipts, gas outputs, miner sectors, power, deals, FEVM traces — into TimescaleDB or CSV, and
from there into the `lily-data.lily` BigQuery public dataset. It was built by the Sentinel team
at Protocol Labs and has been maintained by Starboard since. Roughly forty normalized tables
per network exist because Lily produces them; the Spacescope API, the Grafana dashboards network
monitoring runs on, and a long tail of analyst notebooks and SP tools all read downstream of it.

Maintenance has narrowed to keeping the build alive. The last four releases are Lotus dependency
bumps (v0.24.4, 2026-05-18, was three Lotus bumps and nothing else); the last feature release
was v0.24.3 in January 2026. The data-dumps page still describes a snapshot from January 2023.
Nothing about the pipeline is currently observable from outside: there is no public endpoint that
says how far behind chain head the indexer is, so a stall is discovered by a consumer noticing
missing rows.

This grant funds six months of sustaining maintenance with three specific pieces of work:

1. **Network-version readiness.** NV28 upgraded mainnet on 2026-05-27 with actors v18; NV29
   skeletons are already merged upstream in `go-state-types` and `filecoin-ffi`. Lily needs the
   v19 actor shims, the schema migration and the new FIP state models tagged *before* the
   upgrade epoch, not after — a late Lily means a gap in every dataset downstream of it.
2. **Close the DDO-era modelling gap.** Direct Data Onboarding (NV22) moved onboarding off the
   deal-proposal path, and Lily still models it as pre-DDO market deals.
   `SectorContentChanged` panics on parse (#1317, open since 2024-09), and
   `builtin_actor_events` over-matches (#1360). Consumers currently under-count onboarding and
   compensate with private side-pipelines. This is the same pre-DDO fragility other ProPGF
   chain-data work is funded to route around.
3. **Make the pipeline observable and the dataset fresh on a schedule.** Publish
   `https://lily.starboard.ventures/status.json` — head lag, newest epoch loaded to BigQuery,
   missing-epoch ranges, per-table state — and automate the BigQuery load so freshness is a
   commitment rather than a best effort. This is also what makes every metric in 3.2 checkable
   by ProPGF without asking us for a number.

## 2.2  Who does this work support?

- Pods
- Network Infrastructure
- Application Builders
- Storage Providers

## 2.3 Total Funding Requested (USD)

USD $150,000 (over a 6-month term, Nov 2026 – Apr 2027)

## 2.4 Milestones & Budget

**Milestone 1 — NV29 readiness & observability (Nov 2026 – Jan 2027) · $75k**
- Due: 2027-01-31 · Funding requested: USD $75,000
- Completion criteria:
  - Lily maintainer, 3 months of service — $45k
  - Data/infra engineer at 0.4 FTE, 3 months — $18k
  - Archive-capable Lily node, TimescaleDB, BigQuery storage and loads, 3 months — $12k
  - NV29 actor shims (v19), schema migration and new-FIP models merged on `master`, with a
    release candidate tagged and running against a Calibnet NV29 rehearsal
  - `status.json` live and stable: `head_lag_epochs`, `bigquery_max_height`, `loaded_at`,
    `missing_epochs`, `tables[]`, refreshed every 5 minutes, no auth
  - Data-dumps and data-models documentation refreshed to the current schema (the 2023-01-06
    snapshot removed)

**Milestone 2 — DDO coverage & scheduled freshness (Feb 2027 – Apr 2027) · $75k**
- Due: 2027-04-30 · Funding requested: USD $75,000
- Completion criteria:
  - Lily maintainer, 3 months of service — $45k
  - Data/infra engineer at 0.4 FTE, 3 months — $18k
  - Node, TimescaleDB and BigQuery costs, 3 months — $12k
  - NV29 support released on or before the mainnet upgrade epoch; NV30 skeleton merged
  - DDO onboarding representable end-to-end without pre-DDO deal tables: `SectorContentChanged`
    parses (#1317 closed), verifreg claim state modelled, `builtin_actor_events` filter fixed
    (#1360 closed)
  - BigQuery load automated on a daily schedule, backfill gaps in the trailing 30 days closed,
    freshness reported in `status.json`
  - Runbook published and a second maintainer able to run a release unaided

## Objective 1

Indirect

## Objective 2

Indirect

## Objective 3

Indirect

## 3.1 Impact pathway

Output:
- a Lily release supporting each network version shipped during the term, tagged before the
  upgrade epoch;
- DDO-era onboarding modelled in the public schema rather than approximated from pre-DDO deal
  tables;
- a public, unauthenticated pipeline-status endpoint;
- a daily-loaded `lily-data.lily` BigQuery public dataset with stated freshness;
- current documentation for the schema and the dumps.

Outcome:
- open Filecoin datasets stay continuous across network upgrades instead of gapping for weeks;
- consumers stop maintaining private side-pipelines to compensate for DDO under-counting;
- a stalled indexer is visible to everyone the same hour it stalls, including to ProPGF;
- new analysts and Pods query a documented dataset instead of reverse-engineering table
  semantics from the code.

Impact:
- the ecosystem keeps one free, vendor-neutral chain-data substrate. Every dashboard, funding
  decision and SP-economics analysis that cites network numbers is measuring something Lily
  produced; when it drifts, the numbers the network governs itself with drift with it.

## 3.2 Verification metrics

| Metric | Data source | How it's measured | Target (end of grant) |
|---|---|---|---|
| Index freshness (head lag) | `status.json` (published in M1) | `head_lag_epochs` sampled hourly; share of samples within target | ≥95% of hourly samples within 120 epochs (~1h) of chain head |
| Public dataset freshness | `status.json` → `bigquery_max_height`, `loaded_at` (dataset `lily-data.lily`) | Age of the newest epoch present in the BigQuery public dataset | Newest epoch ≤24h old on every daily check |
| Continuity / backfill gaps | `status.json` → `missing_epochs`, trailing 30 days | Count of epochs with no indexed tipset | No gap longer than 1h; any gap backfilled within 7 days |
| Network-version readiness | GitHub releases, `filecoin-project/lily` | A tagged release supporting the NV's actor bundle, dated on or before the mainnet upgrade epoch | NV29 support tagged before the upgrade epoch; NV30 skeleton merged |
| DDO-era model coverage | Lily repo issues + `status.json` → `tables[]` | DDO onboarding paths populated (verifreg claims, `SectorContentChanged`); #1317 and #1360 closed | Onboarding representable without pre-DDO deal tables |
| Spacescope read API availability | Spacescope API (`api.spacescope.io`) | Uptime over the measurement window | ≥99% monthly — **auth-gated today**, see 3.4 |

## 3.3 References

- BigQuery public dataset: `lily-data.lily` (location `us-east4`)
- Docs, data models and dumps: https://lily.starboard.ventures
- Sentinel: https://github.com/filecoin-project/sentinel
- Open modelling gaps cited above: `filecoin-project/lily` #1317, #1360
- NV28 shipped 2026-05-27 (actors v18, FIP-0112/0113/0114); NV29 skeletons merged upstream

## 3.4 Public verification endpoints — **`NEW — proposed`**

One row per surface ProPGF may read directly. We keep these public for the grant term.

| URL / dataset | Auth | Field ProPGF reads | Refresh | Available |
|---|---|---|---|---|
| `https://lily.starboard.ventures/status.json` | None | `head_lag_epochs`, `bigquery_max_height`, `loaded_at`, `missing_epochs[]`, `tables[]` | 5 min | **To publish by M1 (2027-01-31)** |
| `https://api.github.com/repos/filecoin-project/lily/releases` | None | `tag_name`, `published_at` | On release | Live today |
| `lily-data.lily` (BigQuery) | Google account, requester pays | `MAX(height)` per table | Daily after M2 | Live today, but not anonymously readable — mirrored into `status.json` so ProPGF does not need BigQuery credentials |
| `https://api.spacescope.io` | Bearer token | Availability | — | **Not anonymously readable.** Unlock: an unauthenticated `/health` path. Starboard operates this; we will raise it, but cannot commit to it in this grant |

## 4.4 Core Team

- Lily maintainer (Lotus internals, actor shims, schema migrations) — 1.0 FTE
- Data/infra engineer (node operation, TimescaleDB, BigQuery loading, status endpoint) — 0.4 FTE
- Documentation and release support drawn from the Starboard team as needed

## 4.5 Has your team received a ProPGF grant or funding from PLFIF before?

No

## 5.1 Key risks & dependencies

- **Lotus release cadence.** Lily tracks Lotus and `go-state-types`; NV29 shims cannot be
  finished before the upstream bundle stabilizes. Mitigation: build against the NV29 skeleton
  from day one and rehearse on Calibnet, so the remaining work at bundle-freeze is small.
- **Overlap with other funded chain-data work.** ProPGF Batch 2/3 funds a sector/deal oracle
  and a public sector database explicitly scoped to replace pre-DDO sources and, in places, to
  replace Lily tables for specific consumers. That is a reasonable direction; funding both
  without a boundary is not. Mitigation: agree at kickoff which consumers move to the new
  source and which stay on Lily, and drop from our scope anything the oracle covers. We would
  rather hand over a table than double-fund it.
- **Key-person risk.** The Sentinel team that built Lily has wound down; maintenance knowledge
  sits with a small number of people. Mitigation: the M2 runbook and second-maintainer
  criterion exist for this reason, and are a completion criterion rather than a nice-to-have.
- **Archive-node and infra cost drift.** An archive-capable Lily node plus TimescaleDB plus
  BigQuery loads is the bulk of the non-labour budget and scales with chain size and FEVM
  volume. Mitigation: costs reported per milestone; if they exceed the line item we reduce
  retained history depth before reducing freshness.
- **The Spacescope API is not ours to commit to.** It is operated by Starboard on tables loaded
  from Lily. We can commit to the pipeline and the BigQuery dataset; we can only advocate for
  an unauthenticated health path on the API (see 3.4).

## Anything else you want to share that we didn't ask?

### Why this is a sustaining grant and not a rebuild

Lily works. The chain gets indexed, the tables are correct, the dataset is public and free. What
has lapsed is the maintenance rhythm: releases have become Lotus bumps, the docs describe a
2023 snapshot, and the DDO gap has been open for two years because there is no funded owner to
close it. Six months of a funded maintainer restores that rhythm for roughly what one quarter of
a replacement pipeline's design phase would cost — and any replacement inherits the same
per-upgrade actor-shim work Lily already carries.

### What we are deliberately not asking for

No new tables beyond DDO coverage, no query layer, no dashboards, no API of our own. If the
committee wants a hosted query surface over the dataset, that is a separate application from
whoever is best placed to run it.

### On measurement

We would rather be measured on freshness than on commits. Repo activity is a poor proxy for a
pipeline — an indexer can be committed to weekly and still be six hours behind head. That is
what `status.json` is for, and it is why we put it in M1 rather than M2.

---

# Proposed new fields (not in the current form)

## `1.7 Kernel function(s) this work maintains`

**Type:** multi-select from the `registry/_kernel.yaml` inventory, ordered (primary first), plus
a free-text "propose an inventory addition" escape hatch. Stores the verbatim function string
along with its tier / category / sub-category.

**Why.** Nothing in the current 22 fields identifies the kernel function. `1.5 Category` offers
"Core Infrastructure", which covers most of the inventory, and reviewers currently infer the
function from the 2.1 prose. That inference is exactly where attribution errors get made, and
the inventory has slots where inference cannot work: Essential · Coordination & Incentives ·
Network data & monitoring holds three distinct functions, so a team landing there is ambiguous
until it names the string. Downstream, the monitoring pipeline requires the tuple to match the
inventory character-for-character and rejects a shared slot with no function named — so a
committee decision recorded in prose has to be re-derived by hand before anything can be
measured. Asking the applicant closes that loop, and the free-text escape hatch turns
"nothing fits" into a reviewable inventory PR instead of a borrowed slot.

**Secondary benefit:** unfunded and over-subscribed functions become visible at intake rather
than after the batch closes.

## `3.4 Public verification endpoints`

**Type:** repeating row — URL or dataset, auth requirement, field to read, refresh cadence,
available now vs. by which milestone.

**Why.** `3.2 Verification metrics` already asks for a data source, and teams answer honestly
with things like "grant records", "review reports" or "dashboard inventory" — private artifacts
that no pipeline can read. In one Batch 3 application, five of six proposed metrics had no
public machine-readable source, which surfaced only during a hand audit weeks after approval. A
separate field with an auth column forces the distinction at submission time: a row with
`auth: none` and a named field is monitorable, and anything else is a request for the committee
to fund or unlock a surface. It also gives the applicant a place to say "by M1" — the Lily
`status.json` row above is a commitment the grant pays for, and reads very differently from a
source that will never be public.

**Keep 3.2 as is.** It is the team's own account of what success looks like. 3.4 is the narrower
question of what a machine can check, and separating them means neither has to be watered down.
