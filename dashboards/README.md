# Dashboards

**One notebook.** `propgf-kernel-public.py` is the ProPGF monitoring dashboard, hosted in the
`filecoin` org on oso.xyz as `propgf-kernel-health-live`:

<https://www.oso.xyz/filecoin/propgf-kernel-health-live/view>

The `/view` suffix matters — that URL is readable without an account, while the bare
`/filecoin/propgf-kernel-health-live` is the editor path and redirects to `/login`.

It reads the two `filecoin.filpgf_public.*` mart tables and nothing else, queries live and embeds
no data, so any OSO API key reproduces every number on it.

**Publishing is manual.** Merging a change here does not update the hosted page; someone has to
republish it. `publishedNotebookByName{sourceHash}` is exactly `sha256sum` of this file, so that is
how you check whether the hosted copy matches `main`.

## Two notebooks were retired on 2026-09-14

`propgf-kernel-health.py` (the internal committee view: landing tables + `funding_model_static.*`,
adjudication state, the Batch-3 funding slate) and `propgf-kernel-mockup_v2.py` (the design
reference the public page was built from) are gone, from this repo and from the platform.

The mockup was already inert — its embedded payload was stale by design and kept rendering dropped
`Reiers/*` drafts and two removed Blockscout metrics, which is why the public page was rebuilt to
query live in the first place.

The internal one was a problem. It had been published, and a published notebook renders whatever it
queried into a static page: its `funding_model_static.*` values were reachable at
`/filecoin/propgf-kernel-health/view` with no account, no cookie and no API key. **A notebook that
reads private models must never be published.** If the committee needs that view again, run it
locally with `marimo run` and leave it unpublished.

## `propgf-kernel-public.py`

Built entirely from the two public mart tables
(`filecoin.filpgf_public.kernel_timeseries_metrics_by_project` and `kernel_functions`),
so any OSO API key reproduces every number on it. Nav, hero tier ladder, objective,
timeline, tier cards, a two-tab inventory (by project / by function) with expandable rows,
program coverage tiles, method and glossary.

Three deliberate departures from the design reference it was built from, each because the public
tables cannot support the claim:

- **No money.** The design reference's committed-amount tiles and per-project USD bars are gone; the
  bar now tracks reading coverage. What a grant is worth belongs on no public page.
- **Coverage, not SLA.** Every threshold was withdrawn on 2026-08-20, so the slot the
  reference filled with "SLA met - 90d" carries reading coverage instead: the share of the
  periods a metric's own cadence expects that carry a value. Gaps are drawn amber and
  described as ours, never as a breach.
- **No source block.** The mart carries how each reading was taken (`method`) but not the
  endpoint or the SQL that reduces it to a scalar, so the card names the collection route
  and the Method section says the endpoint is missing on purpose.

### What the denominator is allowed to charge a team for

Both rules live in the `collection_policy` cell, are stated on the page, and were added
2026-08-26 after every Ankr commitment read 26% for reasons that were entirely ours:

- **`COVERAGE_FROM = "2026-08-22"`** — coverage is judged from the day unattended nightly
  collection became the record, never from a metric's first ad-hoc probe. 41 commitments
  across 17 teams carry a single `live-review` reading on 2026-07-15; anchoring the
  denominator on it charged each of them for the month before the instrument existed. It
  is a floor, not an override: a metric first collected later still starts at its own
  first reading.
- **`PLATFORM_OUTAGES = {"2026-08-22", "2026-08-23"}`** — the two nights OSO's run-group
  change made `run { id }` a 400 and every fetch for all twelve teams returned nothing.
  Those periods leave the denominator outright rather than counting as gaps. Dated by hand
  because the public mart has no error column — only `method` — so there is nothing to
  pattern-match on, and a list you must edit by hand cannot quietly swallow a source that
  really did go dark. A weekly or monthly bucket only drops if the outage cost the *whole*
  period.

The stylesheet is character-for-character the mockup's, plus three rules: a blue strip bar
for "read, unscored", a slate one for a period our own platform lost (`--k-skip`), and an
amber `.pill.gap`.

## Run it

```bash
# from the repo root
uv sync --extra dashboards
uv run marimo run dashboards/propgf-kernel-public.py     # read-only app view
# or, to edit:
uv run marimo edit dashboards/propgf-kernel-public.py
```

Set `OSO_API_KEY` in your environment (an [Open Source Observer](https://www.oso.xyz) API key)
so the notebook can query the warehouse live:

```bash
export OSO_API_KEY=...    # or put it in a .env the shell loads
```

## Data sources

Two tables, and deliberately no others:

- `filecoin.filpgf_public.kernel_timeseries_metrics_by_project` — every reading, with the bar as
  it stood that day.
- `filecoin.filpgf_public.kernel_functions` — the kernel inventory, including the functions
  nothing measures yet, so coverage has an honest denominator.

Both are public-read, which is what lets the page claim any OSO API key reproduces every number on
it. `docs/public-datasets.md` is the contract for those tables. Nothing here reads
`funding_model_static.*`, and nothing here should: that is how the retired internal view ended up
publishing private funding values.

## No offline fallback, on purpose

The page has no bundled snapshot. Without a reachable warehouse the query fails and the cell
errors, which is the intended behaviour — a dashboard that silently falls back to stale embedded
data is worse than one that visibly cannot answer. Every number is either live or absent.

One row per commitment-day is chosen at render (`_preferred()`): a reading with a value beats a
null, and among readings with a value the `nightly` one wins over a `backfill:` reconstruction. The
mart applies the same null-versus-value rule one layer earlier, so this is belt-and-braces for the
case the mart deliberately leaves alone — two rows that BOTH carry values.
