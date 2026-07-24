"""Render a ProPGF grant-recipient appendix from a team's manifest + a per-team facts file.

Merges two sources:
  - registry/<team>.yaml + registry/drafts/<team>.yaml -> the monitored SLAs (metric, source,
    threshold, cadence, statement). Thresholds marked ``PLACEHOLDER`` in the manifest are flagged
    "(to confirm)" via the facts file's ``placeholder_thresholds`` list.
  - contracts/<team>.facts.yaml                        -> everything the manifest doesn't carry:
    recipient, scope, committed amount, term, verification metrics, which SLA(s) double as the
    incident signal (and its lead-in/note text), requested-but-not-yet-monitored additions, and
    the dependents/dependencies tables.

Output is a single markdown appendix:
  header block -> §1 Ecosystem Alignment (+ repo link), §2 Public Sources, §3 Monitored
  Commitments (SLAs, then the incident SLA(s) under their lead-in, then requested additions),
  §4 Dependents and dependencies (tables from facts), §5 Reporting.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from fpm.drafts import split_draft
from fpm.kernel import Kernel, load_kernel
from fpm.manifest import FunctionSpec, load_manifest

# Static appendix prose. Team-specific text lives in the facts file, not here.
S1 = (
    "The Grant Recipient affirms that the funded work is designed to support the continued "
    "maintenance of one or more functions of the Filecoin Kernel. The Filecoin Kernel (the "
    '"Kernel") is the published set of functions that the Filecoin Network cannot operate '
    "without."
)
S2 = (
    "The Recipient agrees to keep every source listed below open and usable for monitoring:\n\n"
    "- Endpoints stay publicly reachable — no authentication, credentials, or paid access.\n"
    "- Polling at the stated cadence is permitted.\n"
    "- ProPGF may derive metrics from these endpoints and publish analysis on filpgf.io.\n"
    "- If a source will be retired, changed, or moved behind authentication, the Recipient gives "
    "ProPGF 30 days' notice and proposes a replacement.\n\n"
    "If an endpoint is unreachable for reasons outside the Recipient's control, the measurement "
    "is recorded as unavailable — not as a miss."
)
S3_INTRO = (
    "The Recipient agrees to expose public endpoints so the community can monitor the health and "
    "progress. By reviewing this you agree that the mentioned source and metric are aligned with "
    "what you would like to track. Note: this will be used for reporting purposes. Please suggest "
    "any change or additions you think are necessary."
)
S3_ADDITIONS = (
    "**Requested additions (source needed from the recipient)**\n\n"
    "ProPGF would like to monitor the following, but no public signal exists today. Please propose "
    "a source and threshold, or tell us what you could expose:"
)
S4_INTRO = (
    "List your top three in each direction: the three things your work would break without "
    "(dependencies), and the three projects, teams, or services that would break without your "
    "work (dependents).\n\n"
    "Prioritise what is close to the network — other Filecoin clients, protocols, services, "
    "storage providers, or ProPGF-funded work — over generic infrastructure (cloud providers, "
    "language runtimes, ubiquitous libraries) that isn't specific to Filecoin. The test: if this "
    "link broke, would a Filecoin function degrade? If a generic dependency really is a single "
    "point of failure, include it and say why.\n\n"
    "*Example below pre-filled by ProPGF for illustration — the Recipient should confirm, correct, "
    "or replace each row.*"
)
S5 = (
    "### Automated reporting\n\n"
    "- ProPGF refreshes the metrics regularly and publishes them to **filpgf.io** on a monthly "
    "basis, attributed to the Recipient.\n"
    "- The Recipient will have the ability to flag factual errors or add context before "
    "publishing, but ProPGF publishes on schedule.\n"
    "- The Recipient keeps its releases, changelogs, and incident history publicly available for "
    "the grant term.\n"
    "- The Recipient is welcome to publish any additional updates, reports, or context about the "
    "funded work on **filpgf.io** — this is optional.\n\n"
    "### Filecoin Slack\n\n"
    "The Recipient will join `#filecoin-kernel updates`, the public channel on the Filecoin Slack "
    "shared by all Kernel projects, and will use it as its primary community communication channel "
    "for the funded work. Specifically, the Recipient will:\n\n"
    "1. **Post relevant updates** — including progress against this Appendix, release "
    "announcements, and notice of any incident as they occur.\n"
    "2. **Be responsive to discussion** — replying to direct questions about the funded work in "
    "the channel.\n\n"
    "Because the channel is public, activity in it may be referenced in public reporting and "
    "reviewed at check-ins.\n\n"
    "### Check-ins (every two months)\n\n"
    "ProPGF schedules a check-in call with the Recipient every two months, between the assigned "
    "ProPGF (filpgf) member and the project's lead maintainer. Confirmed dependents are welcome to "
    "join.\n\n"
    "Standing agenda:\n\n"
    "1. Metrics since the last check-in, including any misses and their resolution.\n"
    "2. Proposed changes to metrics, sources, or thresholds, if any.\n"
    "3. Blockers where ProPGF or the ecosystem can help unblock the Recipient.\n"
    "4. Changes to the dependency and dependent picture.\n\n"
    "No milestone reporting is prepared for these calls. (ProPGF runs no program activity in "
    "December — check-ins skip that month and resume in January.)"
)


def _num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else str(v)


def _metric_block(metric: str, source: str, threshold: str, statement: str) -> str:
    """The four-line Metric/Source/Threshold/Statement bullet shared by §3 SLAs and
    the requested-additions block (which passes blank source/threshold)."""
    return (
        f"- **Metric:** `{metric}`\n"
        f"- **Source:** {source}\n"
        f"- **Threshold:** {threshold}\n"
        f"- **Statement:** {statement}\n"
    )


def _sla_block(fn: FunctionSpec, to_confirm: bool = False) -> str:
    url = fn.source.endpoint or fn.source.base_url or "(no public source yet)"
    confirm = " (to confirm)" if to_confirm else ""
    thr = (f"`{fn.sla.metric} {fn.sla.threshold_op} {_num(fn.sla.threshold_value)}`, "
           f"cadence {fn.sla.cadence}{confirm}")
    return _metric_block(fn.sla.metric, url, thr, fn.sla.statement)


def _table(rows: list[dict] | None, keys: list[str]) -> list[str]:
    """Markdown body rows for a numbered table: '| i | row[k1] | ... |' per row."""
    return [f"| {i} | " + " | ".join(str(r.get(k, "")) for k in keys) + " |"
            for i, r in enumerate(rows or [], 1)]


def build_contract(
    facts: dict, functions: list[FunctionSpec], kernel: Kernel
) -> str:
    """Render the §1–§5 grant-recipient appendix. Pure: no file or network I/O.

    ``kernel`` is currently unused by this function; it is kept in the signature for
    interface stability (callers, including the CLI, already pass it).
    """
    ir = facts.get("incident_response") or {}
    incident_ids = set(ir.get("slas", []))
    placeholders = set(facts.get("placeholder_thresholds", []) or [])

    health = [fn for fn in functions if fn.function_id not in incident_ids]
    incident = [fn for fn in functions if fn.function_id in incident_ids]

    L: list[str] = []
    # ---- header ----
    L.append("# ProPGF Batch 3 — Grant Recipient\n")
    L.append(f"#### Contract: {facts['recipient']}\n")
    L.append("_DRAFT / prototype — generated from the team's monitoring manifest. Not executed._\n")
    L.append("| | |")
    L.append("|---|---|")
    L.append(f"| **Recipient** | {facts['recipient']} |")
    L.append(f"| **Point of contact** | {facts.get('contact', 'TODO')} |")
    L.append(f"| **Application** | {facts['app_ref']} |")
    L.append(f"| **Scope** | {facts['scope'].strip()} |")
    req = facts.get("total_requested_usd")
    requested = f" (of ${req:,} requested)" if req else ""
    L.append(f"| **Committed (through {facts['committed_through']})** | "
             f"${facts['committed_usd']:,}{requested} |")
    L.append(f"| **Term** | {facts['term'].strip()} |")
    L.append("")
    if facts.get("verification_metrics"):
        L.append("**Verification metrics in application**\n")
        for m in facts["verification_metrics"]:
            L.append(f"- {m}")
        L.append("")

    # ---- appendix ----
    L.append("# Appendix 1 — Filecoin ProPGF Grant Recipient Commitments\n")

    L.append("## 1. Ecosystem Alignment Obligation\n")
    L.append(S1 + "\n")
    L.append(f"{facts['repo_url']}\n")

    L.append("## 2. Public Sources\n")
    L.append(S2 + "\n")

    L.append("## 3. Monitored Commitments\n")
    L.append(S3_INTRO + "\n")
    for fn in health:
        L.append(_sla_block(fn, to_confirm=fn.function_id in placeholders))
    if incident:
        if ir.get("lead_in"):
            L.append(ir["lead_in"].strip() + "\n")
        for fn in incident:
            L.append(_sla_block(fn, to_confirm=fn.function_id in placeholders))
        if ir.get("note"):
            L.append(ir["note"].strip() + "\n")
    if facts.get("requested_additions"):
        L.append(S3_ADDITIONS + "\n")
        for a in facts["requested_additions"]:
            L.append(_metric_block(a.get("metric", ""), "", "", a.get("statement", "")))

    L.append("## 4. Dependents and dependencies\n")
    L.append(S4_INTRO + "\n")
    L.append("### Top dependents — who relies on this work\n")
    L.append("| # | Dependent | How it depends on this work | Contact (optional) |")
    L.append("| :--- | :--- | :--- | :--- |")
    L += _table(facts.get("dependents"), ["name", "how", "contact"])
    L.append("")
    L.append("### Top dependencies — what this work relies on\n")
    L.append("| # | Dependency | What breaks without it | Owner / maintainer | "
             "ProPGF funded? | Substitutable? |")
    L.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    L += _table(facts.get("dependencies"),
                ["name", "breaks", "owner", "propgf_funded", "substitutable"])
    L.append("")

    L.append("## 5. Reporting\n")
    L.append(S5 + "\n")
    return "\n".join(L)


def load_team_functions(team: str, registry: str = "registry") -> list[FunctionSpec]:
    """Adopted manifest functions + draft functions (drafts render with the same fields)."""
    reg = Path(registry)
    functions = list(load_manifest(reg / f"{team}.yaml").functions)
    draft_path = reg / "drafts" / f"{team}.yaml"
    if draft_path.exists():
        functions += list(split_draft(draft_path)[0].functions)
    return functions


def run_contract_cli(team: str, facts_path: str, registry: str, out: str | None) -> int:
    facts = yaml.safe_load(Path(facts_path).read_text())
    functions = load_team_functions(team, registry)
    kernel = load_kernel(Path(registry) / "_kernel.yaml")
    md = build_contract(facts, functions, kernel)
    if out:
        Path(out).write_text(md)
        print(f"wrote {out} ({len(md)} chars, {len(functions)} SLAs)")
    else:
        print(md)
    return 0
