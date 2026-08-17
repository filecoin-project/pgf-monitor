# filecoin-pgf-monitor — agent guide

Monitoring system for Filecoin ProPGF kernel funding. Teams commit (function, SLA,
source) manifests under `registry/`; the pipeline independently fetches, evaluates,
and lands verdicts. Full picture: `README.md`. Role-specific playbooks:
`docs/guide-projects.md` (teams) and `docs/guide-reviewers.md` (committee).

## Commands

```bash
uv sync                                   # install (Python 3.11+, uv only — never pip)
uv run pytest -q                          # full offline suite; MUST be green before any commit
uv run python scripts/validate_draft.py --all          # drafts: schema+kernel+SQL+allowlist
uv run python -m scripts.validate_pr registry/<team>.yaml   # the PR gate, locally
uv run python scripts/promote_draft.py registry/drafts/<team>.yaml --add-allowlist
uv run fpm review <team> [--store DIR] [--dev-auto-approve] [--live --live-oso --oso-org UUID]
uv run fpm observe [teams...] [--as-of DATE] [--dry-run] [--live-oso --oso-org UUID]  # readings only -> data/observations.csv
uv run fpm report <team> --link URL [--intent "..."] [--out FILE]   # draft an entry from a URL
uv run fpm land --store DIR --oso-org UUID [--public-name N --private-name N]
uv run fpm contract <team> [--facts FILE] [--out FILE]   # render a grant contract from manifest + contracts/<team>.facts.yaml
scripts/demo_project_flow.sh / scripts/demo_reviewer_flow.sh        # offline end-to-end demos
```

Skills (if your harness loads `.claude/skills/`), in program order:
`draft-application` (Karma form, pre-award) · `reconcile-metrics` (decide what a team is measured
on; keep agreement §3, registry, facts and dashboard in agreement) · `author-manifest` (a team
encodes its agreed set) · `review-and-land` (run the pipeline, adjudicate readings, land verdicts).

## Hard rules

- **Never hand-edit another team's `registry/<team>.yaml`** outside a PR; CODEOWNERS
  and the static gate exist precisely to catch that.
- Every `functions[]` entry's (tier, category, sub_category) must match
  `registry/_kernel.yaml` character-for-character — `validate_draft` checks this. When that slot is
  shared by several kernel functions, also set `kernel_function` to the exact inventory name (the
  gate rejects a shared slot without it and lists the choices); it's optional when the slot is unique.
- Exactly one of `source.extract` / `transform` per http-json function. Transform SQL:
  single SELECT, single scalar, only the `raw` table (structural exfiltration guard).
- New source hosts require a `registry/_allowlist.txt` addition in the same PR.
- Thresholds are human commitments: the report drafter deliberately omits them; drafts
  mark ours `PLACEHOLDER`. Don't invent tight thresholds without probe evidence.
- Secrets never enter the repo; live smokes read `OSO_API_KEY` from the environment.
- `data/observations.csv` (values) and `data/thresholds.csv` (the bar as it stood that day) are
  the system of record for the time series — OSO's `filpgf_sla_observations` and
  `filpgf_sla_thresholds` are full-table republishes of them. Never hand-edit either, and never
  write them except through `fpm.observations` / `fpm.thresholds`, which normalize the date and
  dedupe the day. Compliance is NOT stored: the dashboard joins the two on
  (observed_at, team, function_id, metric) and derives pass/fail/unscored/indeterminate at render,
  so a corrected threshold fixes history instead of leaving it judged against a superseded bar.
- Nothing unattended may write a verdict. `.github/workflows/observe.yml` runs `fpm observe`
  (fetch + evaluate, no model); adjudication stays `fpm review` with a human.
- Tests are offline-deterministic; anything live goes in `scripts/live_*_smoke.py`
  (quarantined, never imported by tests).

## Authoring gotchas (cost real debugging time — believe them)

- dlt auto-parses ISO strings to tz-aware timestamps → in transforms use the column
  directly and compare against `:now_tz` (NOT `from_iso8601_timestamp`, NOT `:now`).
- Unix-epoch integer columns pair with the naive binds (`:now` + `from_unixtime`).
- Nested JSON arrays land in unreachable child tables; nested objects flatten to
  `parent__field` columns. Never set `max_table_nesting: 0` with nested arrays.
- Trino integer division truncates — CAST to DOUBLE.
- dlt AUTO-DETECTS a paginator when the config omits one, and GitHub sends Link headers, so a
  `commits?per_page=30` fetch walks the whole history and 403s the unauthenticated 60 req/hour
  budget for every later GitHub metric. `build_ingestion_config` now always sends
  `endpoint.paginator`; never drop it. A `403 rate limit exceeded` on a metric that passes in
  isolation is this, and the real dlt error is in the run log's `extra.error`, NOT `event`
  (which only ever says "Data ingestion failed").
- `source.auth.secret_ref` names an ENV VAR, not an OSO secret: OSO wants the real VALUE in the
  config, lifts it into its own store, and keeps a path-derived marker
  (`{"name": "client.auth.token"}`). Passing a reference name makes it authenticate as that
  literal string -> 401. So the provisioning host (laptop, nightly runner) must hold the
  credential; the repo still holds only the name. Actions secret is `GH_API_TOKEN` because
  Actions reserves the `GITHUB_` prefix.
- Rotating a credential does NOT change the config shape (fingerprints strip secrets, and
  OSO's stored config has no value to compare), so datasets keep the OLD token and 401
  silently. After any rotation run `fpm observe --reprovision`.
- A REST ingestion config CANNOT reference an OSO environment secret by name — tested and
  rejected in all four syntaxes (`{$type:secret,name}`, `secretName`, `{{ secrets.X }}`,
  `{$secret}`). Only a **Python UDM** can (`context.secret("NAME")` with
  `secrets=[...] + environment_name=...`), verified live: core_limit 5000. That path is the
  documented ESCAPE HATCH, deliberately not adopted — arbitrary Python discards the structural
  exfiltration guard (single SELECT, single scalar, one bound `raw` table) that makes accepting
  community-PR sources safe, and UDM code deploys over the API, outside CODEOWNERS and the
  static gate. If it is ever adopted, the UDM source must live in this repo and deploy from CI,
  or `registry/<team>.yaml` stops being the complete answer to how a metric is computed.
- `fpm review` team name = `registry/<name>.yaml` filename stem.
- Trino timestamp literals: `'YYYY-MM-DD HH:MM:SS'` (space, no T, no offset).
- A manifest may omit `sla.threshold` entirely — that is "measured, not scored", and it is the
  honest state for a team whose agreement is missing or whose signed §3 still says "(to confirm)".
  Do NOT invent a number to fill the slot. Set `sla.threshold.source` to `signed-appendix` only
  when you have read it in the signed appendix; it defaults to `provisional` and the dashboard
  labels provisional bars as such.

## Layout

`src/fpm/` pipeline (manifest, provision, adapters, evaluate, observe, observations, thresholds,
detectors, synthesize, pipeline, store, land, report/, governance/, transform/, kernel, drafts) ·
`tests/` mirrors it · `registry/` the trust anchor · `fixtures/` offline responses ·
`dashboards/propgf-kernel-health.py` (marimo, `uv sync --extra dashboards`) ·
`docs/` guides (the grant-commitments appendix + per-plan design docs are gitignored, local only).
