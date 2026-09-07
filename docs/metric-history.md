# Where each metric's history comes from

Two kinds of metric run through this system, and the difference matters more than it sounds.

Some read a **dated event log** at the source: a list of releases, commits, snapshots, incidents.
Ask GitHub next year what `ChainSafe/forest` released on 12 August 2026 and it will still tell you.
Others read a **live gauge**: is this RPC endpoint up, how far behind is the chain head, what is the
pool price. Ask the source tomorrow what that value was yesterday and it has no idea — it never
recorded one.

Which kind a metric is decides three things a funded team and an outside reader both care about:

- **whether a missed day can be recovered.** [`docs/public-datasets.md`](public-datasets.md) notes
  that two metric-days from our 2026-08-22/23 outage were later recovered as real readings while
  "the rest are point-in-time and gone for good." This document is the *why* behind that sentence.
- **whether a threshold can be checked against history before anyone commits to it.** A bar you
  can backtest over 90 days is a different kind of promise from a bar set on three days of readings.
- **how much weight one daily sample carries.** A release cadence computed over a full release
  list is exact. An uptime figure from a single 05:30 UTC probe says nothing about the other
  23 hours.

None of this is a judgement about a team or its infrastructure. It is a property of the API the
metric reads, and it is often fixable by pointing at a different endpoint — see
[Metrics that could gain history](#metrics-that-could-gain-history).

---

## The test

A source has usable history if **you can ask it the same question next year and get the same
answer.** Concretely, three properties:

1. **Each item carries its own timestamp** — `published_at`, `committed_at`, a dated filename.
2. **Each item has a stable ID** — a commit SHA, release tag, block height, snapshot filename.
   This is what lets a re-fetch merge with what we already hold instead of duplicating it.
3. **Items never change once written.**

Health checks, chain heads and current-price endpoints fail all three. They expose no items, no
IDs, and their single value changes every few seconds.

## The split today

Across the 59 SLA entries in `registry/` as of 2026-09-07 (40 adopted and running, 19 in draft):

| | Metrics | Share |
|---|---|---|
| Source keeps its own history | **22** | 37% |
| Our daily reading *is* the history | **35** | 59% |
| No API at all | **2** | 3% |

Sorted by the shape of the API rather than by vendor, the pattern is stark:

| API shape | Metrics | Source keeps history? |
|---|---|---|
| **Event log** — dated, immutable items with stable IDs | 22 | yes, all 22 |
| State snapshot — current roster, price, power | 13 | no |
| Health probe — "am I up right now" | 10 | no |
| RPC pointer — chain head, `eth_call` at `latest` | 10 | no |
| Search count — a `total_count` over a changing set | 2 | no |
| Manual — no endpoint | 2 | n/a |

Twenty-two for twenty-two on event logs, zero on everything else. The shape decides it; no vendor
in this registry is better or worse than another on this axis.

---

## Metrics whose source keeps the history

These 22 come from four kinds of host. The "key" column is the stable ID that identifies an item,
so a later fetch can merge rather than duplicate.

### GitHub releases — 8 metrics · key: release `id`

| Team | Function | Repo |
|---|---|---|
| chainsafe | `forest-release-cadence` | `ChainSafe/forest` |
| filoz | `curio-sealing-release-cadence` | `filecoin-project/curio` |
| filoz | `lotus-consensus-client-release-cadence` *(draft)* | `filecoin-project/lotus` |
| filoz | `evm-eam-actor-maintenance` *(draft)* | `filecoin-project/builtin-actors` |
| filoz | `builtin-actors` *(draft)* | `filecoin-project/builtin-actors` |
| randamu | `drand-release-cadence` | `drand/drand` |
| libp2p-networking | `libp2p-release-cadence` *(draft)* | `libp2p/go-libp2p` |
| zondax | `rosetta-release-currency` | `Zondax/rosetta-filecoin-proxy` |

### GitHub commits — 6 metrics · key: commit `sha`

| Team | Function | Repo |
|---|---|---|
| fil-b | `network-documentation-commit-recency` | `filecoin-project/filecoin-docs` |
| lily | `lily-etl-maintenance` *(draft)* | `filecoin-project/lily` |
| proving | `rust-fil-proofs-maintenance` *(draft)* | `filecoin-project/rust-fil-proofs` |
| proving | `proving-crypto-primitives-maintenance` *(draft)* | `filecoin-project/bellperson` |
| venus | `sophon-miner-maintenance` *(draft)* | `ipfs-force-community/sophon-miner` |
| venus | `damocles-maintenance` *(draft)* | `ipfs-force-community/damocles` |

### GitHub workflow runs — 1 metric · key: run `id`

| Team | Function | Source |
|---|---|---|
| filecoin-data-portal | `network-data-portal-pipeline-freshness` | `davidgasquez/filecoin-data-portal` → `pipeline.yml/runs` |

### Snapshot archive listings — 4 metrics · key: snapshot filename

Host: `forest-archive.chainsafe.dev`

| Team | Function | Path |
|---|---|---|
| chainsafe | `mainnet-snapshot-freshness` | `/list/mainnet/latest-v2` |
| chainsafe | `calibnet-snapshot-freshness` | `/list/calibnet/latest-v2` |
| chainsafe | `mainnet-diff-snapshot-freshness` *(draft)* | `/list/mainnet/diff` |
| chainsafe | `mainnet-lite-snapshot-freshness` *(draft)* | `/list/mainnet/lite` |

### Dated lists elsewhere — 3 metrics

| Team | Function | Source | Key |
|---|---|---|---|
| randamu | `drand-relay-statuspage` | `drand.statuspage.io/api/v2/summary.json` | incident `id` |
| blockscout | `mainnet-block-explorer` | `filfox.info/api/v1/tipset/recent` | tipset `height` |
| libp2p-networking | `mainnet-block-propagation-cadence` *(draft)* | `filfox.info/api/v1/tipset/recent` | tipset `height` |

For all 22, a daily reading is a convenience, not the record. The record is at the source, and any
one of these metrics can be recomputed for any past date from the source itself.

## Metrics where our daily reading is the history

The other 35 ask "how are you *right now*?" — chain head lag, RPC uptime and latency, health
checks, current miner power, current pool price, subgraph indexing freshness.

**For these, the row we write each night is the only record that exists anywhere.** Three
consequences, stated plainly because they affect how the published series should be read:

- **A missed day is a permanent gap.** No backfill is possible; there is nothing to backfill from.
  This is why the 2026-08-22/23 outage left permanent nulls for most commitments and recovered
  only the two whose sources keep their own history.
- **A single sample stands for a whole day.** The nightly run takes one reading at roughly
  05:30 UTC. For a gauge, that is a sample, not a summary — an endpoint that was down for six
  hours in the afternoon reads as healthy, and one that was down for ninety seconds at 05:30 reads
  as broken. Treat a single probe reading as evidence, not proof, and read a run of days rather
  than one day.
- **Thresholds start with no backtest.** For a gauge metric there is no history to check a
  proposed bar against until we have accumulated it ourselves, which is one reason bars on these
  metrics are conservative and marked `provisional`.

## Metrics that could gain history

Twelve of the 35 could move to the "has history" column by **changing the endpoint the metric
reads** — a one-line source change in the team's own manifest, not a change to this system. If one
of these is yours, this is an open invitation:

| Current shape | Candidates | Switch to |
|---|---|---|
| Search count | 2 of 2 | the issue/PR list itself, not `total_count` |
| State snapshot | 6 of 13 | GeckoTerminal OHLCV; Goldsky block-pinned queries; Filfox `/address/{}/messages` |
| Health probe | 3 of 10 | UptimeRobot's ranged-uptime API; Statuspage `/incidents` |
| RPC pointer | 1 of 10 | a block-pinned `eth_call` against an archival node |

The general lesson is worth stating on its own, because it applies to any metric anyone proposes
next: **when a vendor hands you a "right now" number, check whether they also publish the history
behind it.** Search-count endpoints almost always do. Current-state rosters often do. Health
checks and chain heads almost never do — 4 of those 20 have a historical alternative.

The remaining 23 have no such alternative that we have found. If you know of one for a metric of
yours, open an issue or a PR against your manifest; a metric that gains real history is strictly
better for the team being measured, because it can be audited rather than taken on trust.

## The two with no API

`trusted-setup-param-hosting` and `shared-infra-stewardship` (both `filecoin-infra-misc`, draft)
are a manual gateway check and a quarterly committee attestation. There is no endpoint to read, and
we would rather say so than dress up a manual process as a measurement.

---

## What we plan to build

For the 22 event-log metrics we currently keep only the number we happened to read on the days we
looked. We intend to accumulate the source's own list instead — fetch the dated items, store them
keyed on their stable ID so re-fetches merge, and compute the metric as a query over the
accumulated table.

One pattern covers 19 of the 22, so the work is deliberately narrow: GitHub first (15 metrics),
then the snapshot listings (4), which are the same shape against a different host.

Three things improve when it lands:

- Every one of those 22 becomes computable **for any date**, not only for the days we sampled.
- Age-style metrics ("days since last commit") become exact rather than interpolated between
  sampled days.
- Backfill logic in this repo that re-fetches URLs the registry already declares can be retired,
  removing a second implementation that can drift from the first.

Two limits worth naming up front:

- **No retroactive depth.** Accumulating from today forward does not reconstruct the history we
  never held. Existing readings in `data/observations.csv` remain the record for the days they
  cover; this is additive, not a migration.
- **It changes nothing for the other 35.** Routing a gauge metric through the same machinery would
  move the same one-number-a-day into a different table. There is no pipeline that can invent
  history a source never kept.

## Why the record lives in git

A reasonable question from anyone auditing this system: why do readings live in a CSV in a public
git repository rather than only in a data warehouse?

`data/observations.csv` and `data/thresholds.csv` are append-only tables with a merge key and
last-wins semantics — materialized in git rather than in the warehouse. What that buys is
provenance: every reading arrived in a signed, attributable commit; a correction is a visible
commit rather than an in-place edit; and anyone can reconstruct what this system believed on any
past date without asking us. For a monitor whose output informs funding decisions, that property
is the point, and it is not something better merge semantics elsewhere would replace.

So the division we hold, and expect to keep holding:

- **Source facts accumulate in the warehouse** — the 22 event-log metrics above, where the record
  belongs to the source and we are only mirroring it.
- **Our own readings and judgements accumulate in git** — because those are ours, and they should
  be attributable to a commit and a person.

Warehouse-side merge on a stable key is what the first half needs, and it is on the OSO platform
roadmap. Moving the *second* half would be a provenance change, not a performance one, and is not
something we are asking for.

---

## Appendix — one case for a different reason

Two metrics, `chain-love/rpc-endpoint-uptime` and `chain-love/rpc-latency-p50`, are not
well-defined from a single fetch: you cannot compute a percentile from one request. Today they read
UptimeRobot's scrape, which means the sampling and the percentile are the vendor's rather than
ours.

Firing a set of timed requests and computing an honest p50 we own end to end would fix that. It is
a **sampling** improvement, not a history one, and the same argument applies to roughly ten other
head-lag and health metrics where one 05:30 UTC sample is asked to describe a whole day. Worth
doing; independent of everything above.
