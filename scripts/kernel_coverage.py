"""Generate docs/kernel-coverage.md: every catalogued kernel function x who monitors it.

Joins registry/_kernel.yaml against adopted manifests (registry/*.yaml) and drafts
(registry/drafts/*.yaml) on the EXACT kernel function, resolved the same way
`fpm.kernel.conformance_error` resolves it: `kernel_function` when set, otherwise the sole
function in the entry's (tier, category, sub_category) slot. Keying on the triple alone — which
this script used to do — credits every metric in a shared slot to every function in it: 6 of the
17 slots are shared, which is how a published 29/29 came out of a registry that exactly covers
27. An entry that cannot be resolved is reported, never silently spread.

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
from fpm.kernel import load_kernel
from fpm.manifest import load_manifest

OUT = Path("docs/kernel-coverage.md")


def kernel_slots(kernel) -> dict[tuple[str, str, str], list[str]]:
    """(tier, category, sub_category) -> the kernel functions catalogued in that slot."""
    slots: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for e in kernel.entries:
        slots[(e.tier, e.category, e.sub_category)].append(e.function)
    return slots


def resolve_kernel_function(fn, slots) -> tuple[str | None, str | None]:
    """The exact kernel function an entry evidences, or (None, why not).

    Deliberately the same rule as `fpm.kernel.conformance_error`, which the PR gate already
    enforces: if the gate can name the one function an entry is about, so can this.
    """
    slot = (fn.tier, fn.category, fn.sub_category)
    names = slots.get(slot)
    if not names:
        return None, f"{slot} is not a catalogued kernel slot"
    if fn.kernel_function:
        if fn.kernel_function in names:
            return fn.kernel_function, None
        return None, f"kernel_function {fn.kernel_function!r} is not in slot {slot}"
    if len(names) == 1:
        return names[0], None
    return None, f"slot {slot} maps to {len(names)} kernel functions and kernel_function is unset"


def collect():
    """kernel function name -> [entry dicts]; plus declared gaps and unresolvable entries.

    A (team, function_id, metric) declared in BOTH registry/ and registry/drafts/ is ONE entry,
    state `adopted`, flagged `pending_draft`: a draft is how a team's next version is proposed,
    so it must not overwrite what is adopted today (it did, because both were written into one
    dict keyed by slot — ankr's two live metrics were published as `draft` that way).
    """
    kernel = load_kernel()
    slots = kernel_slots(kernel)
    entries = defaultdict(list)  # kernel function -> [entry]
    index: dict[tuple[str, str, str], dict] = {}  # (team, function_id, metric) -> entry
    unresolved = []  # (team, function_id, reason)

    def add(team: str, fn, state: str) -> None:
        name, why = resolve_kernel_function(fn, slots)
        if name is None:
            unresolved.append((team, fn.function_id, why))
            return
        host = host_of(fn.source.base_url) if fn.source.kind == "http-json" else "fixture"
        key = (team, fn.function_id, fn.sla.metric)
        seen = index.get(key)
        if seen is not None:
            # adopted always wins; the loser only records that an update is waiting
            if state == "adopted":
                seen["state"] = "adopted"
            else:
                seen["pending_draft"] = True
            return
        entry = {
            "team": team,
            "function_id": fn.function_id,
            "metric": fn.sla.metric,
            "host": host or "?",
            "state": state,
        }
        index[key] = entry
        entries[name].append(entry)

    for path in sorted(Path("registry").glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        m = load_manifest(path)
        for fn in m.functions:
            add(m.team, fn, "adopted")
    gaps = []  # (team, function, reason)
    for path in sorted(Path("registry/drafts").glob("*.yaml")):
        m, x = split_draft(path)
        for fn in m.functions:
            add(m.team, fn, "draft")
        for u in x.get("unmeasured") or []:
            gaps.append((m.team, u.get("function", "?"), u.get("reason", "")))
    return entries, gaps, unresolved


def counts(entries, kernel) -> dict:
    """The coverage numbers, each named for exactly what it counts."""
    names = [e.function for e in kernel.entries]
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
        "the ONE kernel function it names (`kernel_function`, or the sole function in its slot), "
        "never to every function sharing a slot.",
        "",
        "🟢 adopted, live source · 🟡 drafted, or fixture-only · 🔴 nothing yet.",
        "",
    ]
    cur_tier = None
    for e in kernel.entries:
        if e.tier != cur_tier:
            cur_tier = e.tier
            lines += [f"## {e.tier.upper()}", ""]
        matches = entries.get(e.function, [])
        adopted_live = [m for m in matches if m["state"] == "adopted" and m["host"] != "fixture"]
        mark = "🟢" if adopted_live else ("🟡" if matches else "🔴")
        lines += [f"### {mark} {e.function}", ""]
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
            "## Entries that name no single kernel function",
            "",
            "These are counted toward NOTHING — the generator will not spread a metric across a",
            "shared slot. Set `kernel_function` to the exact inventory name to place them.",
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
        for x in entries.get(e.function, []):
            item = {
                "team": x["team"],
                "function_id": x["function_id"],
                "metric": x["metric"],
                "host": x["host"],
                "state": x["state"],
                "origin": origins.get((x["team"], x["function_id"]), "oso"),
            }
            if x.get("pending_draft"):
                item["pending_draft"] = True
            payload_entries.append(item)
        functions.append(
            {
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
