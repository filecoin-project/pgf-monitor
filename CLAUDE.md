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
uv run python scripts/observations.py void --date D --team T --function-id F --metric M --note "..."  # null a reading that is WRONG, not missing
uv run python -m scripts.exports write                  # regenerate data/kernel_{functions,metrics}.csv from registry/
uv run python -m scripts.exports upload --oso-org UUID  # regenerate, then republish both public static models
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
- New source hosts require a `registry/_allowlist.txt` addition, and it must land in an EARLIER PR
  than the manifest that uses it -- not the same one. `validate.yml` and `dry-run.yml` both read the
  allowlist from the BASE branch, never the PR head, so a host added in the same PR is not yet
  trusted when its metric is checked: the live dry-run reports `egress not allowed (host ... is not
  on the provisioning allowlist)` and the host cannot be proven at all. Land the host first, then
  the metric.
- Any field added to `Manifest`/`FunctionSpec` MUST be classified in
  `src/fpm/governance/fields.py::FIELD_BUCKETS` — `tests/test_governance_fields.py` fails
  otherwise. That one map is what the goalpost diff compares AND what selects functions for the
  live dry-run, so an unclassified field would silently escape both. `trivial` means a change
  provably cannot alter what is measured, how the number is read, or who is accountable; the
  default is `material`.
- Thresholds are human commitments: the report drafter deliberately omits them; drafts
  mark ours `PLACEHOLDER`. Don't invent tight thresholds without probe evidence.
- Secrets never enter the repo; live smokes read `OSO_API_KEY` from the environment.
- **The registry is PUBLIC.** Do not put quoted agreement text, money figures, DocuSign or other
  contract identifiers, or characterisations of a recipient's paperwork into `registry/`. Where a
  bar is absent, say why with `sla.unscored_reason` (an enum) and keep the reasoning in
  `contracts/<team>.facts.yaml`, which is gitignored. `contracts/` being absent is the normal state
  for a collaborator, so nothing in tests or CI may require it.
- **An outside consumer reads `filecoin.filpgf_public.*`, NOT this repo's static models, and
  `docs/public-datasets.md` is that contract.** The mart is TWO tables, kept deliberately minimal —
  `kernel_timeseries_metrics_by_project` (every fact about a reading, including the bar that day) and
  `kernel_functions` (the inventory, incl. the 14 functions nothing measures, so coverage has an
  honest denominator) — both public-read, and it is built by UDMs in
  `insights-private/projects/filecoin/models/` and deployed with that repo's
  `scripts/deploy_models.py`; every model runs `@daily`, so a registry change reaches the mart
  within a day. This repo owns only the LANDING tables it feeds:
  `filpgf_kernel_functions` (the kernel inventory, including functions nothing measures) and
  `filpgf_kernel_metrics` (one row per SLA entry with its join keys: `kernel_id`, `grant_ref`,
  `oso_project_slug`, `team`, `state`, plus `karma_project_id` / `karma_project_slug` resolved from
  `grant_ref` via `_grants.yaml`), beside the two series below. Both are DERIVED from
  `registry/` by
  `fpm.exports` — regenerate with `scripts/exports.py write`, never hand-edit
  `data/kernel_functions.csv` or `data/kernel_metrics.csv`; `tests/test_exports.py` fails when the
  committed copies disagree with the registry. Keep money, agreement terms and contract identifiers
  out of them: `grant_ref` is safe (Karma issues it publicly), what a grant is worth is not.
- `data/observations.csv` (values) and `data/thresholds.csv` (the bar as it stood that day) are
  the system of record for the time series — OSO's `filpgf_sla_observations` and
  `filpgf_sla_thresholds` are full-table republishes of them. Never hand-edit either, and never
  write them except through `fpm.observations` / `fpm.thresholds`, which normalize the date and
  dedupe the day. Compliance is NOT stored: the dashboard joins the two on
  (observed_at, team, function_id, metric) and derives pass/fail/unscored/indeterminate at render,
  so a corrected threshold fixes history instead of leaving it judged against a superseded bar.
- Nothing unattended may write a verdict, and this is now ENFORCED, not just stated:
  `fpm.land.assert_adjudicated` refuses any batch carrying `approver="dev-auto"` (what
  `fpm review --dev-auto-approve` stamps), whole and before publishing anything.
  `.github/workflows/observe.yml` runs `fpm observe` (fetch + evaluate, no model);
  `scripts/run_full_review.sh` refreshes the observation/threshold series and lands NOTHING;
  adjudication stays `fpm review` with a human.
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
`dashboards/` (marimo, `uv sync --extra dashboards`): `propgf-kernel-public.py` is the PUBLIC
surface — hosted as notebook `propgf-kernel-health-live`, built ONLY on the two
`filecoin.filpgf_public.*` mart tables; `propgf-kernel-health.py` is the INTERNAL view (landing
tables + `funding_model_static.*`, carries applicant identity); `propgf-kernel-mockup_v2.py` is a
design reference, served to nobody · 
`docs/` guides (`public-datasets.md` is the consumer-facing contract; the grant-commitments
appendix + per-plan design docs are gitignored, local only).
