# Where each metric's history comes from

Two kinds of metric run through this system, and the difference matters more than it sounds.

Some read a **dated list** at the source: releases, commits, snapshot listings, resolved incidents.
Ask GitHub next year what `ChainSafe/forest` released in August 2026 and it can still tell you.
Others read a **live gauge**: is this RPC endpoint up, how far behind is the chain head, what is the
pool price right now. Ask that source tomorrow what its value was yesterday and it has no idea — it
never recorded one.

Which kind a metric is decides three things a funded team and an outside reader both care about:

- **whether a missed day can be recovered.** [`docs/public-datasets.md`](public-datasets.md) notes
  that two metric-days from our 2026-08-22/23 outage were recovered while "the rest are
  point-in-time and gone for good." This document is the detail behind that sentence.
- **whether a proposed threshold can be checked against history** before anyone commits to it.
- **how much weight one daily sample carries.** A release cadence computed over a release list is
  exact. A head-lag reading from a single 05:30 UTC probe describes one moment of one day.

None of this is a judgement about a team or its infrastructure. It is a property of the endpoint a
metric happens to read, and it is sometimes fixable by reading a different one — see
[Metrics that could gain history](#metrics-that-could-gain-history).

**One caution on reading the tables below.** `team` here is the manifest filename stem, which is
not always the operator of the source being read. `blockscout/mainnet-block-explorer`, for
instance, reads Filfox. `docs/public-datasets.md` makes the same point about `team` versus
`project_display_name`.

---

## The test

A source can answer for a past date if **the same question asked later returns the same answer.**
Three properties:

1. **Each item carries its own timestamp** — `published_at`, `committed_at`, `resolved_at`, a dated
   filename.
2. **Each item has a stable ID** — a commit SHA, release tag, incident id, snapshot filename. This
   is what lets a re-fetch merge with what we already hold instead of duplicating it.
3. **The list reaches back far enough to cover the date you are asking about.**

The third property is a practical limit rather than a principle, and it bites. Our live snapshot
fetch asks for `limit=20`; the backfill script asks the same endpoint for `limit=250`. GitHub lists
are bounded by `per_page` and this pipeline deliberately does not paginate for depth. So "the source
keeps a list" means the source keeps a **window**, and the window's depth is a property of the
endpoint, not a guarantee. Nor are dated items always immutable — a GitHub release can be edited or
deleted after publication.

Live gauges fail the first two properties outright: no items, no IDs, and a single value that
changes every few seconds.

## The split today

Across the 59 SLA entries in `registry/` as of 2026-09-07 (40 adopted and running, 19 in draft):

| Status of past dates | Metrics |
|---|---|
| **Recomputable from the source, and we have actually done it** | 21 |
| Dated items, but no historical query established | 2 |
| Provider publishes *related* history under a different measurement | 3 |
| No historical evidence found anywhere | 31 |
| No live measurement configured yet (fixture placeholder) | 2 |

Sorted by the shape of the endpoint the metric currently reads:

| Endpoint shape | Metrics | Past dates available? |
|---|---|---|
| **Dated list** — timestamped items with stable IDs | 21 | 19 yes, within the source's window; the 2 Filfox rows have no historical query |
| State snapshot — current roster, price, power | 13 | 1 yes (pool volume, from OHLCV candles); 12 no |
| Health probe — "am I up right now" | 11 | 1 yes (drand status, from the incidents endpoint); 10 no |
| RPC pointer — chain head, `eth_call` at `latest` | 10 | no |
| Search count — a `total_count` over a changing set | 2 | no |
| Fixture placeholder — nothing measured yet | 2 | n/a |

The two tables both total 21 by coincidence, not because they name the same metrics: the first
counts what we *can recompute*, the second what shape of endpoint each metric *currently reads*.
Two Filfox rows are dated lists we cannot query historically; two gauge-shaped metrics turn out to
be recoverable from a second endpoint.

The shape of the endpoint decides it, not the vendor. No source in this registry is better or worse
than another on this axis, and two of the exceptions below are cases where a provider we read as a
gauge also publishes a perfectly good history elsewhere.

---

## Metrics we can recompute for a past date

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

### Two we recover from a *different* endpoint than the metric reads — 2 metrics

These are the interesting cases, because the metric as configured reads a gauge, yet the same
provider publishes a history that reconstructs it exactly:

| Team | Function | Metric reads | History comes from |
|---|---|---|---|
| randamu | `drand-relay-statuspage` | `summary.json` — the *current* status indicator | `/api/v2/incidents.json`, with each incident's `created_at` and `resolved_at` |
| secured-finance | `usdfc-axlusdc-pool-volume` | the pool's current trailing-24h volume | GeckoTerminal hourly OHLCV candles, re-summed over the same trailing window |

Both are implemented in `scripts/observations.py` and both have landed real rows in
`data/observations.csv` under `backfill:drand.statuspage.io` and `backfill:api.geckoterminal.com`.
They are the proof that endpoint shape, not provider, is what limits recovery.

### Dated, but with no historical query we have established — 2 metrics

| Team | Function | Source |
|---|---|---|
| blockscout | `mainnet-block-explorer` | `filfox.info/api/v1/tipset/recent` |
| libp2p-networking | `mainnet-block-propagation-cadence` *(draft)* | `filfox.info/api/v1/tipset/recent` |

Tipsets carry heights and timestamps, so the items qualify — but `/tipset/recent` returns only a
recent window and we have not established a way to ask it about a past date. Treated as
unrecoverable until someone demonstrates otherwise.

## Metrics where our nightly reading is the only record

For 31 of the 59, the endpoint reports "how are you right now?" — chain head lag, RPC uptime and
latency, health checks, current miner power, current pool price and peg, subgraph indexing
freshness, the IPNI provider roster — and we have found no historical source for the same
measurement anywhere.

**For these, the row written each night is the only record that exists.** Two consequences worth
stating plainly, because they affect how the published series should be read:

- **A missed day is a permanent gap.** There is nothing to backfill from. This is why the
  2026-08-22/23 outage left permanent nulls for most commitments and recovered only the few whose
  sources keep their own history.
- **A single sample stands for a whole day.** The nightly run takes one reading at roughly
  05:30 UTC. For a gauge, that is a sample, not a summary: an endpoint down for six hours in the
  afternoon reads as healthy, and one down for ninety seconds at 05:30 reads as broken. Read a run
  of days rather than any single day. (Two metrics are exceptions — see the
  [appendix](#appendix--two-metrics-that-report-their-own-window).)

Nothing in this system is scored today: every threshold has been withdrawn pending executed
agreements, as [`docs/public-datasets.md`](public-datasets.md) records. When bars do return, a
gauge metric's bar will have less history behind it than a dated-list metric's, simply because the
history only starts when we start looking.

### Three where a related history exists, but it is a different measurement — 3 metrics

Worth separating from both buckets above, because the distinction is easy to overstate in either
direction:

| Team | Function | Live metric | Related history available |
|---|---|---|---|
| blockscout | `fevm-mainnet-explorer-blockscout` | head-block age | daily indexed transactions, via the stats-service `newTxns` line |
| blockscout | `calibnet-explorer-blockscout` | head-block age | as above, on the testnet host |
| filecoin-infra-misc | `network-monitoring-status-page` *(draft)* | page-update age | incident counts per month, from `status.filecoin.io` |

Rows of this kind are in the series (under `backfill:filecoin.blockscout.com`,
`backfill:filecoin-testnet.blockscout.com` and `backfill:status.filecoin.io`) and carry a note
saying what they are. They are evidence that the service was doing its job on a given day; they are
**not** the committed metric recovered, and should not be read as it.

## Metrics that could gain history

Some of the 31 could move into the recoverable column by **reading a different endpoint from the
same provider.** The two proven cases above began exactly this way, so this is a real avenue rather
than a hopeful one.

Leads we consider worth investigating, none of them yet verified:

| Current shape | Lead |
|---|---|
| Search count (`total_count` of matching issues/PRs) | the issue/PR list itself, with dates, rather than the count |
| State snapshot | provider OHLCV history; block-pinned subgraph queries; per-address message history |
| Health probe | a monitor's ranged-uptime API; a status page's `/incidents` endpoint |
| RPC pointer | a block-pinned `eth_call` against an archival node |

These are leads, not one-line changes. Any of them may need a new selector or new transform SQL,
may need authentication or pagination, and a new source host must be added to
`registry/_allowlist.txt` in an **earlier** PR than the manifest that uses it. Switching a metric's
endpoint also changes what is being measured, so it is a conversation with the team and the
committee, not a config tweak.

The general lesson is the part worth carrying to any metric anyone proposes next: **when a provider
hands you a "right now" number, check whether they also publish the history behind it.** Sometimes
they do, and reading that instead makes the commitment auditable rather than trusted. If you know
of such an endpoint for a metric of yours, open an issue or a PR — a metric with real history is
better for the team being measured, not worse.

## The two with nothing measured yet

`trusted-setup-param-hosting` and `shared-infra-stewardship` (both `filecoin-infra-misc`, draft) are
a manual gateway check and a quarterly committee attestation. Both are declared with the `fixture`
adapter and a placeholder payload — the manifest names a URL, but no live measurement is configured,
and the entries say so in their own SLA statements. They are in the registry so the kernel inventory
has an honest denominator, not because anything is being read.

---

## What we plan to build

For the 21 recomputable metrics we currently keep only the number read on the days we looked. The
plan is to accumulate the source's own dated list instead — fetch the items, store them keyed on
their stable ID so re-fetches merge rather than duplicate, and compute the metric as a query over
the accumulated table. Tracked as `OSO-4981`.

One pattern covers 19 of the 21, so the work is deliberately narrow: GitHub first (15 metrics), then
the snapshot listings (4), the same shape against a different host.

What improves:

- Those metrics become computable **for every date from the day accumulation starts**, rather than
  only for the days we sampled.
- Age-style metrics ("days since last commit") become exact rather than interpolated between
  sampled days.
- Backfill strategies in `scripts/observations.py` that re-fetch URLs the registry already declares
  can be retired, removing a second implementation that can drift from the first.

Two limits, stated up front so the plan is not read as more than it is:

- **No retroactive depth beyond the source's window.** Accumulating forward does not reconstruct
  history the source no longer serves. Existing readings in `data/observations.csv` remain the
  record for the days they cover; this is additive, not a migration.
- **It changes nothing for the other 31.** Routing a gauge metric through the same machinery moves
  the same one-number-a-day into a different table. No pipeline can invent history a source never
  kept.

## Why the readings live in git

A fair question from anyone auditing this system: why do readings live in CSV files in a public git
repository rather than only in a data warehouse?

`data/observations.csv` and `data/thresholds.csv` are append-only tables with a merge key and
last-wins semantics, materialized in git rather than in the warehouse. What that buys is
provenance: every reading arrived in an attributable, timestamped commit; a correction is a visible
commit rather than an in-place edit; and anyone can reconstruct what this system believed on any
past date without asking us. For a monitor whose output informs funding decisions, that property is
the point. (The nightly commits are made by the CI runner and are not cryptographically signed —
what git gives here is attribution and an audit trail, not a signature.)

So the division we hold:

- **Source facts accumulate in the warehouse** — the recomputable metrics above, where the record
  belongs to the source and we are only mirroring it.
- **Our own readings and the bar as it stood each day accumulate in git** — these are ours, and they
  should be traceable to a commit.

Adjudicated verdicts are a third thing and live in neither of those places; they are published to a
separate warehouse table, as [`docs/public-datasets.md`](public-datasets.md) describes.

Warehouse-side merge on a stable key is what the first half of that division needs. Moving the
second half would be a change of provenance model rather than of performance, which is why it is not
on the table here.

---

## Appendix — two metrics that report their own window

`chain-love/rpc-endpoint-uptime` and `chain-love/rpc-latency-p50` are worth calling out because they
are the exception to "a single sample stands for a whole day."

Both read Chain.Love's own monitoring feed, and both are **operator-reported aggregates over the
provider's own window**: the uptime figure is availability across a trailing window, and the latency
figure is a `response_time_p50_seconds` that the monitor has already computed from its own samples.
One fetch of an aggregate is not the same thing as one probe, so these two do not carry the
single-sample caveat that the other gauge metrics do.

What they do carry is a different property: the sampling is the operator's, so the metric is
self-reported by design — which is normal for uptime reporting and is stated in each SLA statement.
Sampling the endpoint independently would produce a *different* measurement rather than a more
accurate one, and would be a change to what was agreed, so it is not something to do quietly. The
same is true of roughly ten head-lag and health metrics where one 05:30 UTC probe stands in for a
day: the fix there is more samples, which is a change to the commitment, not a bug in it.
