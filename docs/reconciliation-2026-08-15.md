# Reconciliation, 2026-08-15 — the signed appendix is the source of truth

A systematic review of every Batch 3 Appendix 1 §3 against `registry/`. The prompt was five
failing readings on 2026-08-15 that were about to be adjudicated; the review found that most of
them could not be adjudicated at all, because nobody had signed the commitment being breached.

The governing principle, decided this session: **the signed Appendix 1 §3 is the source of
truth.** Where the registry disagreed with a signed document, the document wins. Where the
registry carried a metric with no signed §3 behind it, that metric is not a commitment and is
no longer scored as one.

## What changed

### Thresholds and sources corrected to match the signed document

| Team | Was | Now | Source |
|---|---|---|---|
| oif-ipni | `ipni_error_free_ratio >= 0.95` | `>= 0.90` | §3, agreement `1LSw0hk1…` |
| chain-love | polls `api.chain.love` | `filecoin.chain.love` | §3, agreement `1u_7hLjX…` |

Both flagged MATERIAL by the goalpost gate, which is correct — the IPNI change is a deliberate
loosening, and §2 only obliges a recipient to keep *the listed source* public, so we had been
monitoring a Chain.Love host that carried no commitment. The new host was probed live: 200 JSON
on both functions.

Neither change flips a verdict. IPNI's 0.877 reading breaches 0.90 as well as 0.95.

### Money (facts files, gitignored)

Corrected against the `ProPGF Batch 3 Funded list` column **"Committed (thru Dec)"**, which is
authoritative — not Exhibit B arithmetic.

| Team | Was | Now | Why |
|---|---|---|---|
| oif-ipni | 280,000 | 85,000 | 280,000 is the TOTAL contract value; 85,000 is due by Dec 31 |
| ankr | 14,000 | 28,000 | both tranches (Jul 31, Dec 31) fall on/before committed_through |

`randamu` was checked and left at 31,000: the Funded list says 31,000, even though that
agreement's Exhibit B dates every tranche in 2027. The sheet governs; the date discrepancy is a
document problem, not a facts-file error.

### Demoted to `registry/drafts/` — no signed §3 behind them

`fpm observe` globs `registry/*.yaml`, so a draft is defined and coverage-visible but not
observed and not adjudicable. Nightly metric count drops 47 → 32.

**`filoz` split.** The signed §3 (agreement `1wdQmU72…`) commits FilOz to exactly three Curio
metrics. Five others moved to `registry/drafts/filoz.yaml`:
`lotus-consensus-client-release-cadence`, `lotus-miner-winningpost-block-production`,
`evm-eam-actor-maintenance`, `pdp-active-providers`, `builtin-actors`.

The manifest's own comment already conceded the point — those entries were marked
"PRE-EXISTING FilOz agreements … included so kernel coverage is complete for the steward",
which is a coverage rationale, not a commitment. `builtin-actors` is the metric that failed on
2026-08-15; landing that verdict would have asserted an obligation FilOz never signed.

The Funded list's WIP "Impact Metrics" column does name all five for Curio (FilOz), so the
intent existed — it just never reached the executed §3. Promote when the §3 is amended with
FilOz's agreement, or when the pre-existing Lotus/lotus-miner agreements are located.

**Five whole manifests with no counterparty at all** — OSO-authored, `@TODO-github-handle`
maintainers, thresholds ours, and absent from the Funded list entirely:
`filecoin-infra-misc`, `proving`, `lily`, `venus`, `libp2p-networking`.

These are real ecosystem telemetry filed in a schema whose noun is "commitment". Publishing
them to filpgf.io as team accountability misrepresents what they are. They remain as drafts so
the kernel-coverage map still shows the function is watched.

### Annotated but left adopted

- **blockscout** — the team replaced §3 with two bare health-check URLs, no thresholds. The
  ≤3600s bars are ours. Marked placeholder pending check-in.
- **chainsafe** — conflates two grants: Forest (§3, $252,000) and *Filecoin Infrastructure
  Services (ChainSafe)* ($8,400, a Batch 2 amendment through March 2027) whose four metrics the
  Funded list names exactly. Backed, but by a contract not yet located. Split once found.
- **zondax** ($79,000) and **filecoin-data-portal** ($140,000) — funded, metrics named on the
  Funded list, but no Batch 3 agreement exists on the Drive. Thresholds are ours.
- **secured-finance** — §3 matches the registry exactly, so no drift; but Exhibit A says
  "Liquidity capital itself is explicitly not part of this request". The grant funds
  measurement of pool depth, not provision of it. Committee call, not a registry fix.

## Defects found in the documents themselves

These need legal/ops, not code:

1. **Ankr's agreement carries drand's §3 and §4 verbatim** — five beacon metrics for relays
   Ankr does not operate. The two metrics we actually measure them on appear nowhere in their
   contract. (Forest and Secured Finance had the same paste and are fixed; Ankr is not.)
2. **Stacked pre-kernel appendices** — Plumbline has two Appendix 1 sections, js-libp2p has
   three. The old block ("Monthly Milestone Reporting Requirement", "the four official Filecoin
   ecosystem metrics") contradicts the current one.
3. **Impossible dates** — IPNI Exhibit B "Feb 30, 2027"; Blockscout "February 30, 2027" and
   "September 31, 2027".
4. **Unfilled placeholders** — Ankr's signature block still reads `PROJECT NAME` / `ADDRESS`.
5. **Unexpressible commitments** — Forest signed two metrics the pipeline cannot evaluate
   (two-source compare; a month-over-month delta read from a date-templated markdown file).
   They read as monitored and will never fire.
6. **js-libp2p** has a signed §3 metric (`js_libp2p_ci_health`) with no manifest at all.
7. **Beryx** is funded ($12,000) with a facts file and no manifest — zero monitoring.
8. **Slack channel** is "#filpgf" in some agreements and "#filecoin-kernel updates" in others.

## Consequences for the 2026-08-15 readings

Of the five breaches that triggered this review:

| Breach | Status after reconciliation |
|---|---|
| filoz `builtin-actors` | **Not adjudicable** — demoted; no signed commitment |
| secured-finance `pool-tvl` | **Do not land** — grant explicitly excludes liquidity provision |
| oif-ipni `error_free_ratio` | Real, now scored against the signed 0.90 |
| plumbline `qap_share` | Real and cleanly landable (caveat: filfox is a third-party source) |
| filecoin-data-portal `pipeline_success_age_days` | Real signal, but threshold is ours and unconfirmed |

## Not done in this pass

Locating the missing agreements (ChainSafe Infra Batch 2 + amendment, Zondax, Filecoin Data
Portal); a beryx manifest; regenerating `badges.json` and `docs/kernel-coverage.md`; rebuilding
the hand-built dashboard payload in `dashboards/propgf-kernel-mockup_v2.py`, which still
references demoted entries.
