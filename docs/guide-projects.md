# Project guide — own your kernel-monitoring manifest

You received ProPGF funding (or steward a kernel function under a pre-existing
agreement). This repo is where you declare, in public, **what function you serve, what
"healthy" means, and where the evidence comes from**. The pipeline fetches your source
independently on a schedule, evaluates it against your SLA, and lands the verdicts in a
public warehouse table the committee and community can query.

Follow it yourself, or hand it to a coding agent (Claude Code, Cursor, etc.) verbatim —
it works either way. Everything is runnable offline except the final PR.

## One-time setup

```bash
git clone https://github.com/filecoin-project/pgf-monitor
cd pgf-monitor
uv sync
uv run pytest -q        # ~200 tests, no network, should be all green
```

## 1. Find your manifest

Most funded teams already have a manifest at `registry/<team>.yaml`, running live — OSO
seeded these from public sources so the board wasn't empty on day one, with the research
notes preserved as comments. Find yours and refine it. If there isn't one yet, start a
draft at `registry/drafts/<team>.yaml`.
Each entry carries **probe evidence** (when we checked your endpoint, what we saw) and
**placeholder thresholds** (marked `PLACEHOLDER`, with our rationale).

Your job: make the manifest *yours*.

- Replace `maintainers: ["@TODO-github-handle"]` with real GitHub handles (these gate
  who can approve changes to your file via CODEOWNERS).
- Confirm or change each metric. You know your service better than we do — if there is
  a better health signal (a status endpoint, a metrics API), swap it in.
- Set thresholds you are willing to be held to. The SLA `statement` should read as a
  plain-English promise.
- Anything genuinely unmeasurable (coordination work, quality judgments) belongs in
  `x_draft.unmeasured` with a reason — honesty beats theater.

## 2. The manifest contract (what an entry means)

```yaml
- function_id: mainnet-snapshot-freshness     # stable id, kebab-case
  origin: external-pr                         # lineage: oso (OSO-authored) | karma
                                              # (from your Karma application's "3.2
                                              # Verification metrics" answer) | external-pr
                                              # (you submitted it). Defaults to oso.
  tier: essential                             # + category/sub_category: copied EXACTLY
  category: 'Blockchain Core & Physical Storage'   # from registry/_kernel.yaml —
  sub_category: 'Mainnet Infrastructure'           # the catalogued kernel taxonomy
  oso_project_slug: forest                    # links your OSO track record
  sla:
    statement: "Newest mainnet snapshot <= 6h old, measured daily"
    metric: snapshot_age_hours
    threshold: { op: "<=", value: 6 }
    cadence: daily                            # daily | weekly | monthly
  source:
    adapter: oso
    kind: http-json                           # public JSON over HTTP
    base_url: "https://forest-archive.chainsafe.dev"
    endpoint: "https://forest-archive.chainsafe.dev/list/mainnet/latest-v2?format=json"
    query: "/list/mainnet/latest-v2?format=json"
    extract: { column: uploaded_at, timestamp_column: uploaded_at, cast: date,
               reduce: latest, derive: age_seconds, unit: seconds }
```

Two ways to turn a response into a number:

- **`extract`** — declarative: pick a column, reduce (`single|latest|avg|min|max|null_ratio`),
  derive (`value|diff|age_seconds|age_days`).
- **`transform`** — one bounded Trino SQL SELECT over your response table (aliased
  `raw`), returning a single scalar. No joins, no other tables — structurally enforced.
  Time binds: `:now`/`:window_start`/`:window_end` (naive, for unix-epoch columns) and
  `:now_tz`/... (tz-aware, for ISO timestamp columns). Exactly one of extract/transform.

Gotchas the validator will catch (and some it can't):
- Nested JSON **arrays** land in child tables your transform cannot reach — metrics must
  be computable from top-level fields. Nested **objects** flatten into columns
  (`result.Height` → `result__height`).
- Never set `max_table_nesting: 0` on a source with nested arrays — the fetch fails.
- Your source host must be on `registry/_allowlist.txt` before merge. Drafts declare
  the additions they need in `x_draft.allowlist_additions`; the committee approves them
  with your PR.

## 3. Validate locally (fast, offline)

```bash
uv run python scripts/validate_draft.py registry/drafts/<team>.yaml
uv run pytest tests/test_drafts_conformance.py -q
```

`validate_draft` runs everything the PR gate will run: schema, kernel-taxonomy
conformance, transform-SQL safety, allowlist status. Fix `FAIL` lines; `note` lines
about the allowlist are expected until the committee merges your additions.

Probe your own source the way the pipeline will see it:

```bash
curl -s "<your endpoint>" | head -c 2000    # is it JSON? are your fields there?
```

## 4. Drafting a brand-new entry (optional)

If you're adding a function from scratch, the drafter can do the probe-and-infer for you:

```bash
uv run fpm report <team> --link "https://api.example.org/health" \
    --intent "prove our relay keeps pace with the beacon" --out /tmp/entry.yaml
```

It probes the link, infers a plausible extract, and emits a schema-valid entry with the
threshold deliberately left as a TODO — thresholds are a human commitment. (`--live`
uses a real model for the inference; without it a deterministic heuristic runs.)

## 5. Promote and open the PR

```bash
uv run python scripts/promote_draft.py registry/drafts/<team>.yaml --add-allowlist
git rm registry/drafts/<team>.yaml
git checkout -b <team>/adopt-monitoring
git add registry/ && git commit -m "feat(registry): <team> adopts kernel monitoring manifest"
gh pr create
```

What happens on the PR:
1. **static-gate** (always, no secrets): schema, allowlist, config translation,
   transform validation, kernel conformance, and a **goalpost report** — any loosening
   of an existing SLA (threshold, cadence, source swap) is classified and surfaced to
   reviewers. Changing goalposts isn't forbidden; doing it quietly is.
2. **live-dry-run** (committee applies the `dry-run-ok` label): provisions your source
   in OSO for real, fetches, and posts the observed value — proving the entry works
   before merge.
3. **CODEOWNERS review** and merge. From then on you're on the public dashboard.

## Changing your SLA later

Edit `registry/<team>.yaml` in a PR. The same gate runs; material goalpost moves are
labelled in the diff report and reviewed by the committee. Keep the `function_id`
stable — it is the join key for your verdict history.
