# Dummy Lily application → complete Appendix 1: what maps, what's missing

> Companion to `docs/dummy-application-lily.md` (fictional). Worked through the `reconcile-metrics` workflow (then named `author-appendix`)
> workflow on 2026-08-05 and **rendered** to prove the map produces a document:
> `uv run fpm contract lily --facts <scratch>/lily.facts.yaml` → 1 SLA, 6 requested additions.
> The facts file lives in the session scratchpad, not `contracts/`, so no fiction lands next to
> real grant terms. `git status registry/ contracts/` clean.

## 1. Field-by-field map

| Application field | Appendix destination | Status |
|---|---|---|
| 1.1 Project Name, 1.3 Website | header **Recipient** | Application gives the project, the agreement gives the **legal entity**. Need Exhibit A. |
| 1.2 Project Github | §1 repo link (`facts.repo_url`) | Have |
| 1.4 Team Lead/Point of Contact | header **Point of contact** | Placeholder in the dummy; a real submission supplies it |
| **1.7 Kernel function(s)** *(proposed)* | §1 — **nothing prints it today**, see §5 | Would remove the reviewer's inference step entirely |
| 2.1 Summary + 2.4 Milestones | header **Scope** (`facts.scope`) | Have — condensed to one paragraph |
| 2.3 Total Funding Requested | header `total_requested_usd` | Have ($150k) |
| 2.4 milestone due dates | `committed_through` | **Exhibit B only.** Rendered `TODO` on purpose |
| — | `committed_usd` | **Exhibit B only** — amount due *by* `committed_through`, not the grant total |
| 3.1 Impact pathway (Outcome) | §4 dependents | Have — three evidence-backed rows |
| 3.2 Verification metrics | header verbatim list **and** §3 (see below) | Have verbatim; §3 needs classification |
| 3.3 References | evidence for §4, not rendered | Have |
| **3.4 Public endpoints** *(proposed)* | §2 obligation + each §3 **Source** line | This is the field that decides §3 vs requested-addition |
| 4.4 Core Team | not in the appendix | — |
| 4.5 Prior funding | not in the appendix | — |
| 5.1 Key risks & dependencies | §4 dependencies | Have — three rows, one of them a scope boundary |
| "Anything else" | not in the appendix | — |

## 2. §3 classification — the actual work

Rule applied: public JSON, no auth, field readable **today** → SLA. Everything else → requested
addition with a named unlock.

| Application 3.2 metric | Verdict | Metric id | Why |
|---|---|---|---|
| — (adopted manifest) | **SLA** | `lily_days_since_last_commit` | Only readable signal today. Threshold 90d unconfirmed → `placeholder_thresholds` → renders "(to confirm)" |
| Index freshness (head lag) | Addition → SLA at M1 | `lily_head_lag_epochs` | `status.json` doesn't exist yet |
| Public dataset freshness | Addition → SLA at M1 | `lily_bigquery_data_age_hours` | BigQuery needs a Google account and is requester-pays; mirror `bigquery_max_height` + `loaded_at` into `status.json` |
| Continuity / backfill gaps | Addition → SLA at M1 | `lily_missing_epochs_30d` | Same endpoint. Head lag doesn't catch a hole behind a caught-up indexer |
| Network-version readiness | Addition, **reshaped** | `lily_supported_network_version` | The application's form ("release tagged before the upgrade epoch") isn't measurable — a release can be on time and not carry the bundle. Needs `supported_nv` on `status.json`. **Do not** substitute release cadence |
| DDO-era model coverage | Addition, **delivery gate** | `lily_ddo_tables_populated` | Milestone-shaped: reads as unmet every month until it lands, then passes permanently (the `cuzk-upstream-prs` pattern). Flag it or track it as a milestone |
| Spacescope API availability | Addition | `spacescope_api_availability` | Bearer-token gated. Unlock: unauthenticated `/health` |

**The headline: one unlock buys four SLAs.** Publishing
`https://lily.starboard.ventures/status.json` — unauthenticated, `head_lag_epochs`,
`bigquery_max_height`, `loaded_at`, `missing_epochs[]`, `supported_nv`, `tables[]` — converts five
of the six additions into monitored commitments and retires the repo-activity proxy the manifest
itself calls insufficient. The application already commits to it in Milestone 1, so the appendix
can carry those five as additions now and repoint them at signature-plus-one-milestone.

**Unresolved contradiction to settle before signature:** the application calls the Spacescope API
"not ours to commit to". If the recipient is the Starboard entity that operates it, that doesn't
hold and §2 applies. Either the entity commits, or the row is dropped — it can't be both.

## 3. Manifest work (`registry/lily.yaml`)

The manifest is the only source for §3, so these block a complete appendix:

- `maintainers: ["@TODO-github-handle"]` (line 10) — team fills in
- `oso_project_slug: starboard-ventures` (line 24) — carries a TODO; confirm the steward
- Threshold `<= 90` days (line 28) — a guess; either confirm with the team or keep it in
  `placeholder_thresholds`
- **`lily.starboard.ventures` is not in `registry/_allowlist.txt`** — a `status.json` SLA needs an
  allowlist addition in the same PR, which is a committee decision
- Each new function needs the full tuple (tier / category / sub_category / `kernel_function`
  verbatim) plus an `extract` or `transform`, and `status.json` is a flat object → `reduce: single`

## 4. Kernel attribution — a real finding

The dummy claims two inventory functions. The second one is a problem:
`"Aggregates Filecoin on/off-chain data into open, queryable datasets and dashboards"` is
**already claimed by three teams** — `goldsky` (×2), `filecoin-data-portal`, `secured-finance`
(×2). Lily claiming it too makes it a four-way attribution. Recommendation: Lily claims only
`"Chain ETL, indexing, normalization & parameter matching (BigQuery, Spacescope API)"`, which
nothing else claims and which is what the funded work actually maintains.

The third entry in that slot, `"Chain ETL and indexing"` (empty `value`, unclaimed), looks like a
duplicate of Lily's function. Merge it or attribute it — leaving it open invites the next
applicant to land there and split the function in two.

## 5. Renderer gaps this exercise exposed

Both are small and both affect real Batch 4 appendices, not just this dummy:

1. **`src/fpm/report/contract.py:150` hardcodes `# ProPGF Batch 3 — Grant Recipient`.** A November
   2026 application is Batch 4. Needs a `batch` field in the facts file.
2. **§1 never names the kernel function.** It asserts alignment with "one or more functions of the
   Filecoin Kernel" and then doesn't say which — even though `build_contract` already receives the
   loaded kernel and the manifest already carries the tuple (`contract.py:135-140` notes the
   argument is unused). Printing tier / category / sub-category / function under §1 is a few lines,
   and it's what makes the appendix self-contained as a commitment document. Proposed field 1.7
   feeds it directly.

## 6. Ready-to-sign checklist

From the agreement (nobody else can supply these):

- [ ] Legal entity and signatory
- [ ] Exhibit B: `committed_usd` (due by `committed_through`) and the milestone dates
- [ ] Exhibit A vs application 2.4 — diverge often; §3 follows Exhibit A
- [ ] Real app_ref, replacing `APP-EXAMPLE-LILY01`

From the team:

- [ ] Maintainer GitHub handle and point of contact
- [ ] Confirm or replace the 90-day commit threshold
- [ ] Confirm the `status.json` field names and the M1 date
- [ ] Confirm, correct, or replace every §4 row (one already carries a `TODO — Recipient to name`)
- [ ] Resolve the Spacescope commitment question

From the committee:

- [ ] Allowlist `lily.starboard.ventures`
- [ ] Kernel slot: single claim vs two, and what happens to `"Chain ETL and indexing"`
- [ ] Scope boundary against the ProPGF-funded sector/deal oracle, which is separately funded to
      replace Lily tables for named consumers
