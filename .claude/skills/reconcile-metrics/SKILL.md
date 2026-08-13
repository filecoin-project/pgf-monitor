---
name: reconcile-metrics
description: Use when deciding what a team should be measured on, or when making the four records of that decision agree — the signed agreement's Appendix 1 §3, registry/<team>.yaml, contracts/<team>.facts.yaml, and the dashboard payload. Covers measurability triage, thresholds from evidence, source ownership, the committed-money figure, rendering with `fpm contract`, and diffing against the docs on the Drive. Triggers on "diff the contract against the registry", "check the docs on the drive", "what should <team> be measured on", "reconcile the metrics", "did anyone change their §3", "create/fix the appendix".
---

# Decide and reconcile monitored commitments

Every metric in §3 is something a grantee signs up to and a reviewer will later hold them to.
**Wrong content here is worse than missing content.** The appendix, the manifest and the dashboard
are three places the same commitment is written down; this skill is how they stay honest and how
they stay in agreement.

## New here? Read this first

`README.md` explains the program and the kernel in five minutes; `docs/guide-reviewers.md` is the
committee-side playbook this skill sits inside. The words below appear constantly and are assumed
everywhere after this point:

| Term | What it is |
|---|---|
| **the kernel** | The functions the network cannot operate without, catalogued in `registry/_kernel.yaml`. A team is funded to maintain one or more of them. |
| **manifest** | `registry/<team>.yaml` — one team's public declaration: which kernel functions it maintains, the metric for each, the public source, and the threshold it commits to. |
| **the registry** | All of `registry/` together. The trust anchor: what actually gets measured. CODEOWNERS-guarded. |
| **Appendix 1** | The "ProPGF Grant Recipient Commitments" section of a signed grant agreement. **§1** alignment · **§2** keeping sources public · **§3** the monitored commitments · **§4** dependents/dependencies · **§5** reporting. §3 is the one that must match the manifest. |
| **facts file** | `contracts/<team>.facts.yaml` — recipient, scope, money and §4 content used to render the appendix. Gitignored; local only. |
| **the payload** | The registry snapshot embedded in the dashboard notebook, gzip+base64 on one line. Hand-built, so it drifts (see *Drift*). |

Prerequisites: `uv sync` once. Reading the agreements needs Google Drive access. Nothing in this
skill writes to the registry without a pull request.

## Which direction are you going?

The two jobs share all the discipline below but invert the ground truth. Decide first.

**Authoring** — no commitment exists yet, or a proposed one needs judging. The registry is the
target; you are writing into it. Ground truth: what the team can actually expose today.

**Reconciling** — commitments exist in more than one place and disagree. The signed document wins;
the registry follows it. This is the common case now that Batch 3 is signed, and teams amend their
own §3 without telling anyone.

## Ground truth

Authoring order:

1. `registry/_kernel.yaml` — the function slot, character-for-character
2. The project's own artifacts, probed today
3. `contracts/<team>.facts.yaml` — recipient, scope, money, requested additions, §4 (gitignored)
4. The Karma application at `https://app.filpgf.io/applications/<APP-REF>` — *self-proposed* metrics
5. `registry/<team>.yaml` / `registry/drafts/<team>.yaml`

Reconciling order — **inverted at the top**:

1. **The signed agreement's Appendix 1 §3** on the Drive. If a team rewrote it, that is the
   commitment; the registry is now stale, not the document.
2. `ProPGF Batch 3 Funded list` — authoritative for money (see step 8)
3. `registry/<team>.yaml` — what we are currently measuring
4. `contracts/<team>.facts.yaml`
5. The dashboard payload — a snapshot, and the most likely to be wrong

## Where the documents are

The **`Batch 3 agreements`** Drive folder (`1RL1BUun-uO34Iy4rV8eFO4FnoxuwVBn1`, owned by
sejal.rekhan@protocol.ai) is the canonical home **but is not complete**. On 2026-08-13 the newest
Curio, Open Model and Ankr agreements all lived *outside* it, and the Ankr copy inside the folder
was two weeks stale. Always search the whole Drive by title and sort by `modifiedTime`; never trust
the folder listing alone. Standalone appendices live in its `Missing Appendices` subfolder.

Goldsky and Zondax had no Batch 3 agreement on the Drive at all as of 2026-08-13.

## Workflow

1. **Identify the track.** Kernel-track teams have a manifest and get §3 monitored commitments.
   Non-kernel teams (`synaps3`, `js-libp2p`, Open Model) get **zero** §3 entries — everything goes
   in requested additions, `committed_through: "TODO — non-kernel track"`, `committed_usd` omitted.
   A manifest entry needs a real `registry/_kernel.yaml` slot; if no slot fits, that is the format
   telling you the work is outside the kernel. Do not borrow an unrelated slot to force it in.

2. **Verify the recipient owns the app_ref.** Cross-check `app_ref` in the facts file against the
   application and the agreement. A shared app_ref between two teams means someone has conflated
   them — resolve it before writing anything. (2026-07-30: three `Reiers/*` repos were staged under
   `team: filoz` on the premise they were FilOz's Curio repos. They were not — `Reiers` is TSE
   Reiersen, the **Plumbline** operator. The draft was dropped in `d9aea65`, but the repos survived
   on the published dashboard for two more weeks; see *Drift* below.)

3. **Probe every source, now.** Never take a threshold, an endpoint, or an activity claim from a
   review doc, a dossier, or a previous render — they go stale.
   ```bash
   uv run python scripts/probe_sources.py --team <team>     # registry sources, reachability only
   ```
   For anything new, `curl` it and read the actual fields. Parse JSON with a parser: `grep -c` on
   single-line JSON counts lines, not items, and will silently give you 1.

4. **Classify each proposed metric.** Public JSON, no auth, field readable today → §3. Anything
   else → requested addition, and name **the specific unlock** ("publish the settlement contract
   address plus a subgraph over it"), not just "no source". Group metrics that share one unlock and
   say so — it turns six asks into one. Never invent a proxy metric to fill space.

   **Check the shape is expressible before promising it.** Public and readable is not sufficient.
   These all appeared in signed Batch 3 §3 sections and **none is supported today**:

   | Shape | Seen in |
   |---|---|
   | Two-source compare (endpoint vs upstream releases) | chainsafe upgrade-readiness, ankr version lag |
   | Delta vs previous period ("no month-over-month decrease") | chainsafe API conformance |
   | Date-templated URL (`report_<YYYY-MM-01>.md`) | chainsafe conformance report |
   | Non-JSON source (markdown) | same |
   | Tiered threshold keyed to another reading | secured-finance peg band by pool depth |
   | No threshold, "published for context" | secured-finance ×2 |
   | On-chain contract call (`getRedemptionRate()`) | secured-finance |
   | Second-source exemption rule (null rounds ≠ miss) | ankr |

   A commitment the pipeline cannot evaluate is worse than a requested addition: it reads as
   monitored and silently never fires. Say so at classification time.

5. **Thresholds are human commitments.** Derive from the probe and say so, or mark the function in
   `placeholder_thresholds` so it renders "(to confirm)". If the observed value sits on the
   threshold, say that rather than shipping a metric that fails on day one. Where the agreement and
   the manifest disagree on a number, **the agreement is what they signed** — IPNI's
   `ipni_error_free_ratio` is `>= 0.90` in the document and `>= 0.95` in the manifest.

6. **Sources must be the recipient's own.** §2 obliges them to keep every listed source public. A
   third-party endpoint (filfox, a coin API) is fine as an internal cross-check but is not theirs
   to commit to — putting it in their §3 makes them liable for someone else's uptime. Check the
   host too, not just the metric: chain-love's manifest reads `api.chain.love` while their
   agreement commits to `filecoin.chain.love`.

7. **§4 needs evidence.** Pre-fill dependents/dependencies only from something you can point at.
   If there's nothing (no stars, no forks, no named integrations), leave a `TODO — Recipient to
   name` row explaining what you looked for. An honest gap beats invented rows.

8. **Money: never guess.** `committed_usd` means *amount due by `committed_through`* (2026-12-31 for
   batch 3), **not the grant total**. That distinction is the whole game — most money errors here
   are a total written into a committed-through field.

   Authoritative source, in order:

   1. **`ProPGF Batch 3 Funded list`** — column **"Committed (thru Dec)"** is exactly this field.
      Its **"Total Contract value"** column is the whole grant; never put that in `committed_usd`.
   2. Exhibit B in the signed agreement — sum the milestones dated on or before `committed_through`
      and check it matches.
   3. `[MasterSheet] ProPGF Batch 3` — **superseded**, and wrong for 4 of 16 teams when the Funded
      list arrived. Use only if the Funded list has no row. Its neighbouring columns are traps:
      *Current $ Projection* is the award total, *Initial Request* is the ask.

   Where two sources disagree, check whether they are answering different questions before picking.
   Ankr looked like a contradiction ($28k in the agreement, $14k in the sheet) and was not: $14k is
   due by December, $28k is the contract. Both were right.

   Omit the field to render "TODO" rather than a misleading `$0` — and note `0` is falsy, so a real
   `$0` renders as "no award this batch", which is how a funded team came to look unfunded.

9. **Render.**
   ```bash
   uv run fpm contract <team> --facts contracts/<team>.facts.yaml --out /tmp/<team>.md
   ```
   To render a **subset** of a team's manifest, or a team that must not enter the registry, build a
   scratch registry instead of splitting the real one:
   ```bash
   R=/tmp/scratch-registry; mkdir -p $R; cp registry/_kernel.yaml registry/_*.json registry/_allowlist.txt $R/
   # optionally write $R/<team>.yaml with only the functions you want
   uv run fpm contract <team> --facts /tmp/<team>.facts.yaml --registry $R --out /tmp/<team>.md
   ```
   Then confirm `git status registry/` is clean. The registry is what gets measured and landed; a
   document need is never a reason to fragment it.

10. **Diff metric-by-metric, and report both directions.** For each team say what the document has
    that the registry lacks, *and* what the registry measures that the document never mentions.
    Never "looks fine". Both directions matter: five teams' documents were ahead of the registry on
    2026-08-13, and FilOz's registry carried five commitments that appear in no signed agreement.

## Drift is the standing failure

Nothing regenerates from the registry, so every downstream copy rots independently. A registry
change is not done until you have checked the copies:

- **`badges.json`** — regenerate with `uv run python scripts/kernel_coverage.py --badges`. It was
  stale by one for three weeks after four registry changes.
- **`docs/kernel-coverage.md`** — same script, no `--badges`.
- **The dashboard payload** (`dashboards/propgf-kernel-mockup_v2.py`, gzip+base64 on one line) is
  **hand-built with no generator**. It kept rendering the dropped `Reiers/*` drafts and two
  Blockscout metrics that had been removed from the manifest. Decode it, diff `(team, fid)` against
  the registry, and remember the project/kernel `e` arrays hold **positions into `entries`** — they
  must be rebuilt whenever an entry is removed, or every row silently shows the wrong cards.

Counting rule, so the numbers can be defended: the badge counts adopted manifests in
`registry/*.yaml`; the dashboard counts project rows, which also include draft-only teams and
funded teams with no manifest at all. 18 vs 20 is not a bug.

## Failure modes seen in the wild

- **Someone else's appendix.** On 2026-07-30, 4 of 12 agreements carried a different grantee's §3
  and §4 — one drand render pasted into Forest ($504k), Ankr and Secured Finance, and Beryx's into
  Goldsky. Always check the §3 metrics belong to the recipient named at the top of the doc.
- **A team rewrote §3 themselves.** Treat it as the new source of truth and repoint the registry,
  rather than reverting them. Check whether their endpoint is *better*: Blockscout moved us to
  `/api/health`, uncached and carrying a health boolean the old path lacked. But check what they
  dropped — ChainSafe's rewrite kept 1 of our 5 and added 2 we had never seen; Secured Finance
  replaced all of theirs; Blockscout's replacement carries endpoints with no thresholds at all.
- **Two Appendix 1 sections stacked.** The old pre-kernel version ("Monthly Milestone Reporting
  Requirement", "the four official Filecoin ecosystem metrics") survives above the new one and
  contradicts it — ours ends "No milestone reporting is prepared for these calls." Delete the old
  block. Still present in Plumbline on 2026-08-13.
- **Stale §4 intro.** Current wording is "List your top three in each direction: the three things
  your work would break without…". The older "Please list your top three… Ring-fence the list…"
  means the appendix came from a render predating 2026-07-24 — check §3 too, it's probably stale.
- **A redacted endpoint.** Ankr's agreement says "url provided" and "Provider's url under
  /filecoin" throughout and never names the host. You cannot adopt what you cannot address.
- **Markdown → Google Doc conversion** leaves §4 header rows as literal bold text under an empty
  header row. Cosmetic and consistent across the existing docs; tidy in Docs if it matters.

## Document mechanics

Secondary to the metrics, but this is where they land.

**Publish** a standalone doc (title `<Team> — Appendix`, body = `# <Team>` then §1–§5) into the
`Missing Appendices` Drive folder, then **read it back to verify**. The `fileSize: 1` in the create
response is stale and does not mean the doc is empty.

**Also worth flagging while you are in there** — not appendix content, but it reaches signature:
unfilled `INSERT PROJECT NAME` / `PROJECT NAME` / `ADDRESS` placeholders; Exhibit B tables with the
Amount column holding dates or missing entirely; impossible dates (February 30 and September 31
both shipped in batch 3, in IPNI and Blockscout); unresolved redline collisions in the body
("thirty (30)seven days'"). Flag them; don't fix Exhibit B yourself.

## Related skills

`draft-application` writes the Karma application *before* an award. `author-manifest` is the
**team** encoding an already-agreed metric set into their own manifest. `review-and-land` runs the
pipeline over metrics that are already flowing and adjudicates the readings. This skill is the
committee-side step between them: deciding what the commitment should be, and keeping every record
of it in agreement.
