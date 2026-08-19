"""Generate docs/kernel-coverage.md: every catalogued kernel function x who monitors it.

Joins registry/_kernel.yaml against adopted manifests (registry/*.yaml) and drafts
(registry/drafts/*.yaml) on the kernel function's slug: each SLA names exactly one via `kernel_id`,
the same rule `fpm.kernel.conformance_error` enforces at the gate. Keying on the
(tier, category, sub_category) triple, which this script used to do, credits every metric in a
shared slot to every function in it: 6 of the 17 slots are shared, which is how a published 29/29
came out of a registry that exactly covers 27. An entry whose id resolves to nothing is reported,
never silently spread.

Two coverage numbers, because both are real and they are not the same claim:
  * ADOPTED    — the function has a metric in registry/, so some team is held to it today.
  * WITH DRAFTS— the function has a metric in registry/ or registry/drafts/, i.e. it is modelled
                 but possibly not yet committed to by anyone.

Usage:
  uv run python scripts/kernel_coverage.py [--write]   # docs/kernel-coverage.md
  uv run python scripts/kernel_coverage.py --embed     # refresh the COVERAGE literal
                                                       # in dashboards/propgf-kernel-health.py
  uv run python scripts/kernel_coverage.py --badges    # write badges.json (README shields read it)
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from fpm.drafts import split_draft
from fpm.governance.allowlist import host_of
from fpm.kernel import NON_KERNEL_ID, load_kernel
from fpm.manifest import load_manifest

OUT = Path("docs/kernel-coverage.md")


def resolve_kernel_id(fn, ids: set[str]) -> tuple[str | None, str | None]:
    """The kernel function an entry evidences, by slug, or (None, why not).

    Deliberately the same rule as `fpm.kernel.conformance_error`, which the PR gate already
    enforces. `NON_KERNEL_ID` resolves to nothing on purpose: the metric is real, it is simply not
    evidence for any catalogued kernel function, so it must inflate no coverage number.
    """
    if not fn.kernel_id:
        return None, "kernel_id is unset"
    if fn.kernel_id == NON_KERNEL_ID:
        return None, None
    if fn.kernel_id in ids:
        return fn.kernel_id, None
    return None, f"kernel_id {fn.kernel_id!r} is not in the kernel inventory"


def collect(registry_dir: Path = Path("registry"), drafts_dir: Path | None = None):
    """kernel function name -> [entry dicts]; plus declared gaps and unresolvable entries.

    Merge rules for the same logical metric — (team, function_id, metric) — declared in both
    registry/ and registry/drafts/, which is how a team proposes its next version:

    * SAME kernel function: one entry, state `adopted`, flagged `pending_draft`. A draft must not
      overwrite what is adopted today (it did, because both files were written into one dict keyed
      by slot — ankr's two live metrics were published as `draft` that way).
    * DIFFERENT kernel function: BOTH are kept — adopted under the function it is assigned to
      today, draft under the one it proposes moving to, and the adopted entry is flagged
      `pending_draft`. Collapsing these would hide a proposed reassignment entirely: the proposed
      function would show no draft coverage at all.
    """
    drafts_dir = registry_dir / "drafts" if drafts_dir is None else drafts_dir
    kernel = load_kernel()
    ids = {e.id for e in kernel.entries}
    entries = defaultdict(list)  # kernel id -> [entry]
    # (team, function_id, metric) -> {kernel function -> entry}. The kernel function is part of
    # the identity, not a property of the record: a draft may move a metric between functions.
    index: dict[tuple[str, str, str], dict[str, dict]] = defaultdict(dict)
    unresolved = []  # (team, function_id, reason)

    def add(team: str, fn, state: str) -> None:
        name, why = resolve_kernel_id(fn, ids)
        if name is None:
            if why is not None:
                unresolved.append((team, fn.function_id, why))
            return  # non-kernel: real metric, no kernel function to credit
        host = host_of(fn.source.base_url) if fn.source.kind == "http-json" else "fixture"
        by_function = index[(team, fn.function_id, fn.sla.metric)]
        seen = by_function.get(name)
        if seen is not None:
            # adopted always wins; the loser only records that an update is waiting
            if state == "adopted":
                seen["state"] = "adopted"
            else:
                seen["pending_draft"] = True
            return
        if state == "draft":
            # a draft assignment elsewhere is a proposed move: say so on what is adopted today
            for other in by_function.values():
                if other["state"] == "adopted":
                    other["pending_draft"] = True
        entry = {
            "team": team,
            "function_id": fn.function_id,
            "metric": fn.sla.metric,
            "host": host or "?",
            "state": state,
            # who is paid, and what code the work covers: the two facts `oso_project_slug` used
            # to conflate. Both ride the payload so the warehouse mapping can be built from it.
            "funded_project": fn.funded_project_oso_slug,
            "repos": sorted(fn.repos),
        }
        by_function[name] = entry
        entries[name].append(entry)

    for path in sorted(registry_dir.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        m = load_manifest(path)
        for fn in m.functions:
            add(m.team, fn, "adopted")
    gaps = []  # (team, function, reason)
    for path in sorted(drafts_dir.glob("*.yaml")):
        m, x = split_draft(path)
        for fn in m.functions:
            add(m.team, fn, "draft")
        for u in x.get("unmeasured") or []:
            gaps.append((m.team, u.get("function", "?"), u.get("reason", "")))
    return entries, gaps, unresolved


def counts(entries, kernel) -> dict:
    """The coverage numbers, each named for exactly what it counts."""
    names = [e.id for e in kernel.entries]
    adopted = sum(1 for n in names if any(x["state"] == "adopted" for x in entries.get(n, [])))
    with_drafts = sum(1 for n in names if entries.get(n))
    live = sum(
        1
        for n in names
        if any(x["state"] == "adopted" and x["host"] != "fixture" for x in entries.get(n, []))
    )
    return {"functions": len(names), "adopted": adopted, "with_drafts": with_drafts, "live": live}


def render() -> str:
    kernel = load_kernel()
    entries, gaps, unresolved = collect()
    c = counts(entries, kernel)
    n = c["functions"]
    lines = [
        "# Kernel coverage matrix",
        "",
        "Auto-generated by `scripts/kernel_coverage.py` — do not edit by hand.",
        "Every catalogued kernel function (registry/_kernel.yaml) and the metrics that",
        "monitor it, from adopted manifests (registry/) plus any pending drafts",
        "(registry/drafts/). `fixture` sources are placeholders awaiting a real feed.",
        "",
        f"**{c['adopted']}/{n} functions are adopted** — a metric in `registry/`, so a team is "
        f"held to it today, and {c['live']} of those read from a live, non-fixture source. "
        f"**{c['with_drafts']}/{n} are modelled** — adopted or drafted. A metric is credited to "
        "the ONE kernel function its `kernel_id` names, never to every function sharing a slot.",
        "",
        "🟢 adopted, live source · 🟡 drafted, or fixture-only · 🔴 nothing yet.",
        "",
    ]
    cur_tier = None
    for e in kernel.entries:
        if e.tier != cur_tier:
            cur_tier = e.tier
            lines += [f"## {e.tier.upper()}", ""]
        matches = entries.get(e.id, [])
        adopted_live = [m for m in matches if m["state"] == "adopted" and m["host"] != "fixture"]
        mark = "🟢" if adopted_live else ("🟡" if matches else "🔴")
        lines += [f"### {mark} {e.function}", "", f"`{e.id}`", ""]
        if e.value:
            lines += [f"> {e.value}", ""]
        if matches:
            lines += ["| team | metric | source | state |", "|---|---|---|---|"]
            for m in matches:
                state = m["state"] + (" (draft update pending)" if m.get("pending_draft") else "")
                lines.append(
                    f"| {m['team']} | `{m['metric']}` ({m['function_id']}) | {m['host']} | {state} |"
                )
            lines.append("")
        else:
            lines += ["_No monitoring entry yet._", ""]
    if unresolved:
        lines += [
            "## Entries whose kernel_id resolves to nothing",
            "",
            "These are counted toward NOTHING. Set `kernel_id` to an id in registry/_kernel.yaml,",
            "or to `non-kernel` if the inventory genuinely does not name what the metric measures.",
            "",
            "| team | function_id | why |",
            "|---|---|---|",
        ]
        for team, fid, why in unresolved:
            lines.append(f"| {team} | `{fid}` | {why} |")
        lines.append("")
    if gaps:
        lines += [
            "## Declared unmeasurable / candidate gaps",
            "",
            "Honest gaps recorded by drafts (`x_draft.unmeasured`):",
            "",
            "| team | aspect | reason |",
            "|---|---|---|",
        ]
        for team, fn_text, reason in gaps:
            lines.append(f"| {team} | {fn_text[:70]} | {reason[:110]} |")
        lines.append("")
    return "\n".join(lines)


DASHBOARD = Path("dashboards/propgf-kernel-health.py")
EMBED_START = (
    "    # COVERAGE-EMBED-START (regenerate: uv run python scripts/kernel_coverage.py --embed)"
)
EMBED_END = "    # COVERAGE-EMBED-END"


def coverage_json() -> dict:
    """The dashboard's embedded coverage payload: every kernel function x its entries."""

    kernel = load_kernel()
    entries, _, _ = collect()
    # lineage per (team, function_id): "oso" | "karma" | "external-pr"
    origins: dict[tuple[str, str], str] = {}
    for path in sorted(Path("registry").glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        m = load_manifest(path)
        for fn in m.functions:
            origins[(m.team, fn.function_id)] = fn.origin
    functions = []
    for e in kernel.entries:
        payload_entries = []
        for x in entries.get(e.id, []):
            item = {
                "team": x["team"],
                "function_id": x["function_id"],
                "metric": x["metric"],
                "host": x["host"],
                "state": x["state"],
                "funded_project": x["funded_project"],
                "origin": origins.get((x["team"], x["function_id"]), "oso"),
            }
            if x["repos"]:
                item["repos"] = x["repos"]
            if x.get("pending_draft"):
                item["pending_draft"] = True
            payload_entries.append(item)
        functions.append(
            {
                "id": e.id,
                "tier": e.tier,
                "category": e.category,
                "sub_category": e.sub_category,
                "function": e.function,
                "entries": payload_entries,
            }
        )
    team_app_refs = {}
    for path in sorted(Path("registry/drafts").glob("*.yaml")):
        m, x = split_draft(path)
        refs = x.get("app_ref")
        if isinstance(refs, str) and refs.strip():
            team_app_refs[m.team] = [r.strip() for r in refs.split(",") if r.strip()]
        slates = x.get("slates")
        if isinstance(slates, list):
            team_app_refs.setdefault(m.team, [])
            for s2 in slates:
                if s2.get("app_ref"):
                    team_app_refs[m.team].append(s2["app_ref"])
    return {"functions": functions, "team_app_refs": team_app_refs}


def embed() -> None:
    import json as _json

    payload = _json.dumps(coverage_json(), indent=None, sort_keys=True)
    text = DASHBOARD.read_text()
    start = text.index(EMBED_START)
    end = text.index(EMBED_END)
    new = (
        text[:start]
        + EMBED_START
        + "\n    COVERAGE = _json.loads(\n        "
        + repr(payload)
        + "\n    )\n"
        + text[end:]
    )
    DASHBOARD.write_text(new)
    print(f"embedded coverage into {DASHBOARD} ({len(payload)} bytes)")


BADGES_JSON = Path("badges.json")


def badges_data() -> dict:
    """The counts shields.io reads, each key naming exactly what it counts.

    `coverage` — the key the README's headline badge points at — is the ADOPTED number: what
    some team is held to today. The draft-inclusive number is published beside it under its own
    key and its own badge, so 27/29 can never be read as 29/29 of anything.
    """
    kernel = load_kernel()
    entries, _, _ = collect()
    c = counts(entries, kernel)
    teams = [p for p in sorted(Path("registry").glob("*.yaml")) if not p.name.startswith("_")]
    n_metrics = sum(len(load_manifest(p).functions) for p in teams)
    n = c["functions"]
    return {
        "kernel_functions": n,
        "monitored_metrics": n_metrics,
        "teams": len(teams),
        "coverage": f"{c['adopted']}/{n}",
        "coverage_adopted": f"{c['adopted']}/{n}",
        "coverage_with_drafts": f"{c['with_drafts']}/{n}",
        "coverage_live": f"{c['live']}/{n}",
    }


def badges() -> None:
    """Write badges.json (the README's shields URLs point at this file on the main branch)."""
    import json as _json

    data = badges_data()
    BADGES_JSON.write_text(_json.dumps(data, indent=2) + "\n")
    print(f"wrote {BADGES_JSON}: {data}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help=f"write {OUT} instead of stdout")
    ap.add_argument("--embed", action="store_true", help="refresh the dashboard COVERAGE literal")
    ap.add_argument(
        "--badges",
        action="store_true",
        help="write badges.json (shields.io reads it for the README count badges)",
    )
    args = ap.parse_args(argv)
    if args.embed:
        embed()
        return 0
    if args.badges:
        badges()
        return 0
    md = render()
    if args.write:
        OUT.write_text(md)
        print(f"wrote {OUT} ({len(md.splitlines())} lines)")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
