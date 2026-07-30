<div align="center">

# The Filecoin Kernel Monitor

Machine-verifiable health monitoring for the Filecoin kernel functions, from public sources.

[Live dashboard →](https://www.oso.xyz/filecoin/propgf-kernel-health)

<!-- counts read live from badges.json via shields.io; regenerate it with: uv run python scripts/kernel_coverage.py --badges -->
<p>
  <img src="https://img.shields.io/badge/dynamic/json?url=https://raw.githubusercontent.com/filecoin-project/pgf-monitor/main/badges.json&query=%24.kernel_functions&label=kernel%20functions&color=0D9488" alt="kernel functions">
  <img src="https://img.shields.io/badge/dynamic/json?url=https://raw.githubusercontent.com/filecoin-project/pgf-monitor/main/badges.json&query=%24.monitored_metrics&label=monitored%20metrics&color=0D9488" alt="monitored metrics">
  <img src="https://img.shields.io/badge/dynamic/json?url=https://raw.githubusercontent.com/filecoin-project/pgf-monitor/main/badges.json&query=%24.teams&label=teams&color=0D9488" alt="teams">
  <img src="https://img.shields.io/badge/dynamic/json?url=https://raw.githubusercontent.com/filecoin-project/pgf-monitor/main/badges.json&query=%24.coverage&label=coverage&color=16A34A" alt="coverage">
  <a href="https://github.com/filecoin-project/pgf-monitor/actions/workflows/validate.yml"><img src="https://github.com/filecoin-project/pgf-monitor/actions/workflows/validate.yml/badge.svg" alt="Validate"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
</p>

</div>

---

The Filecoin ProPGF program funds teams that maintain the network's core functions. This
repo tracks the health of those functions from public sources.

The **Filecoin kernel** is the set of functions the network cannot operate without, split
into irreplaceable and essential tiers and catalogued in
[`registry/_kernel.yaml`](registry/_kernel.yaml). Each funded team declares, in a public
manifest, which kernel functions it maintains and how to check each one: a **metric**, a
**public source** for it, and an **SLA** (the threshold it commits to). The pipeline fetches
each source, evaluates the SLA, and publishes the result. Every value comes from the source,
not from self-reporting.

```
FUNCTION → SLA → SOURCE → READING → EVALUATION → RECOMMENDATION → VERDICT
        (the repo: what was promised)   (the pipeline: what was measured)   (a human: the call)
```

The [live dashboard](https://www.oso.xyz/filecoin/propgf-kernel-health) shows each kernel
function's current status — green (OK), red (a recent interruption), or amber
(indeterminate) — alongside the ProPGF funding for each team.

## Start here

| You are… | Go to |
|---|---|
| A funded team writing or editing your manifest | [docs/guide-projects.md](docs/guide-projects.md) |
| A ProPGF reviewer or committee member | [docs/guide-reviewers.md](docs/guide-reviewers.md) |
| Using a coding agent (Claude Code, Cursor, …) | [CLAUDE.md](CLAUDE.md) — both guides are agent-ready too |
| An agent answering questions without cloning | [SKILL.md](SKILL.md) — point yours at the [raw URL](https://raw.githubusercontent.com/filecoin-project/pgf-monitor/main/SKILL.md) |

## How a team commits to a metric

A commitment is data, not a promise in prose. Each entry in a team's manifest
(`registry/<team>.yaml`) is a metric, a public source, and a threshold:

```yaml
- function_id: mainnet-block-explorer
  origin: external-pr           # who proposed it: oso | karma | external-pr
  tier: essential
  category: 'UX/DX'
  sub_category: 'Explorers and Tooling'
  sla:
    statement: "Explorer keeps pace with the chain: largest gap between indexed tipsets <= 90s"
    metric: explorer_max_tipset_gap_seconds
    threshold: { op: "<=", value: 90 }
    cadence: daily
  source:
    adapter: oso
    kind: http-json
    base_url: "https://filfox.info"
    query: "/api/v1/tipset/recent"
  transform:
    sql: "SELECT MAX(g) FROM (SELECT timestamp - LAG(timestamp) OVER (ORDER BY height) AS g FROM raw) s"
```

The [project guide](docs/guide-projects.md) walks through choosing metrics and sources,
validating offline, and opening the PR.

## Contribute

Changes to `registry/` ride pull requests, so the whole history of what each team promised
is public and auditable. To add or change a metric:

1. Edit your team's manifest, or start a new one under `registry/drafts/<team>.yaml`.
2. Validate it offline: `uv run python -m scripts.validate_pr registry/<team>.yaml`.
3. Open a PR. CI runs the static gate; the committee can trigger a live dry-run before merge.

New source hosts need a line in [`registry/_allowlist.txt`](registry/_allowlist.txt) in the
same PR — approving the PR approves the egress.

## Run it locally

```bash
uv sync
uv run pytest -q                       # full deterministic suite: no network, no model
uv run fpm review chainsafe --manifest tests/fixtures/chainsafe.yaml --dev-auto-approve
uv run python -m scripts.validate_pr registry/chainsafe.yaml
```

Two offline, credential-free demos of the whole loop:

```bash
scripts/demo_project_flow.sh     # a team's loop: draft → validate → dry promotion → gate check
scripts/demo_reviewer_flow.sh    # committee loop: review → adjudicate → verdicts
```

Live modes (real fetches, real dashboard data) need an `OSO_API_KEY` — see the
[reviewer guide](docs/guide-reviewers.md).

## Repo map

```
registry/            the trust anchor (PR-governed, CI-gated)
  _kernel.yaml         the kernel taxonomy (tier / category / sub_category)
  _schema.json         manifest schema      _allowlist.txt   approved source hosts
  <team>.yaml          adopted team manifests, running live
  drafts/<team>.yaml   staging for new proposals, created on demand
src/fpm/             the pipeline: manifest → fetch → evaluate → recommend → adjudicate → land
scripts/             validate_pr (the PR gate), validate_draft / promote_draft, offline demos
dashboards/          propgf-kernel-health.py (marimo; uv sync --extra dashboards)
docs/                guides (project · reviewer · governance · coverage)
.github/workflows/   static gate on every PR + label-gated live dry-run + tests
```

## Governance

`registry/` changes ride PRs. A **static gate** runs on every PR with no secrets: it checks
the schema, kernel-taxonomy conformance, the source-host allowlist, and transform-SQL safety,
and prints a **goalpost report** — a team can't quietly loosen an SLA, because every threshold
change is classified and surfaced for review. The committee's `dry-run-ok` label triggers a
**live dry-run** that provisions the source for real and posts the observed value before merge.
CODEOWNERS keeps each team's file under its own maintainers, and the kernel taxonomy itself
evolves by reviewed PR.

What a funded team owes, and how an SLA is structured, is spelled out in the
[project guide](docs/guide-projects.md).
