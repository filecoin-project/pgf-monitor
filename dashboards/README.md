# Dashboards

Marimo dashboards over the ProPGF monitoring system. Anyone can run them locally; a
hosted copy is published on oso.xyz (filecoin org, notebook `propgf-kernel-health`).

## `propgf-kernel-health.py`

Two views in one notebook:

1. **The Kernel** — all 29 kernel functions as a board of cards, grouped in tier bands
   (irreplaceable → essential). Each function's dot shows one of three signals: green
   (OK), red (a recent interruption), or amber (indeterminate). Click any function to open
   a modal with the metrics behind it — every team × metric, its current reading and
   status, an origin badge (Karma / External PR) where relevant, and a line chart of the
   metric's observed history (or a "latest value" panel for snapshot-only metrics).
2. **ProPGF Funding** — the committee's working slate: who's funded, at what number, for
   which kernel functions. KPI tiles (projects, working total, kernel coverage), a
   working-allocation bar by committee status (Advance / Re-scope / Unresolved), and a
   slate table. Each project has a **reporting** health strip; click a project to see all
   the metrics it owns and which reporting requirements aren't OK.

## Run it

```bash
# from the repo root
uv sync --extra dashboards
uv run marimo run dashboards/propgf-kernel-health.py     # read-only app view
# or, to edit:
uv run marimo edit dashboards/propgf-kernel-health.py
```

Set `OSO_API_KEY` in your environment (an [Open Source Observer](https://www.oso.xyz) API key)
so the notebook can query the warehouse live:

```bash
export OSO_API_KEY=...    # or put it in a .env the shell loads
```

## Data sources

- **Kernel taxonomy:** `filecoin.funding_model_static.requirements` (OSO warehouse).
- **Funding slate:** `filecoin.funding_model_static.decisions` (`csnap-` committee
  snapshot events) + `applicant_identity` + `application_requirements`.
- **Registry coverage** (which team monitors which function, and each metric's `origin`):
  embedded in the notebook — regenerate after registry changes with
  `uv run python scripts/kernel_coverage.py --embed`.
- **SLA verdicts:** `filecoin.filpgf_sla_verdicts` — produced by `fpm review` + `fpm land`.
- **Metric history** (the modal line charts): `filecoin.filpgf_sla_observations` — the
  backfilled + accruing observation time series, maintained by `scripts/observations.py`.
- **Thresholds** (the bar a reading is judged against, as it stood that day):
  `filecoin.filpgf_sla_thresholds` — maintained alongside observations by
  `scripts/observations.py`; the dashboard LEFT JOINs it against observations and derives
  pass/fail/unscored/indeterminate at render time.

## Offline fallback

Without an `OSO_API_KEY` (or if the warehouse is unreachable), the notebook still renders
from a bundled snapshot in `data/kernel_fallback.json` (kernel taxonomy + latest SLA
verdicts + observation history + the funding slate). The published copy on oso.xyz always
renders against live warehouse data.
