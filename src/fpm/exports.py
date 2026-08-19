"""The structural half of the public warehouse surface: what is measured, and where it sits.

`data/observations.csv` says what a metric READ on a day. It cannot say what the metric IS: which
kernel function it evidences, which team and project it belongs to, which grant pays for it, or
whether it is adopted or still a draft. All of that lived in `registry/` and, for rendering, in a
JSON literal embedded in `dashboards/propgf-kernel-health.py` — so nobody outside this repo could
rebuild the by-kernel-function view. These two exports publish it:

  `filpgf_kernel_functions`  the inventory from registry/_kernel.yaml, one row per kernel function,
                             INCLUDING functions nothing measures yet. That is deliberate: a
                             coverage denominator that only lists covered functions always reads
                             100%.
  `filpgf_kernel_metrics`    one row per SLA entry, adopted and draft, carrying the join keys
                             (`kernel_id`, `grant_ref`, `oso_project_slug`, `team`) and enough
                             description to label a chart.

Both are DERIVED from `registry/` — regenerate, never hand-edit. `tests/test_exports.py` fails when
the committed CSVs disagree with the registry, which is what keeps the published tables honest.

Deliberately NOT here:
  * thresholds and compliance. The bar has its own time series (`fpm.thresholds`), and pass/fail is
    derived where it is rendered so a corrected bar re-judges history instead of leaving rows
    measured against a number nobody agreed to. A stored outcome column would be the one copy that
    goes stale.
  * money, agreement terms, contract identifiers. `grant_ref` is safe — Karma issues it and shows
    it publicly — but nothing about what a grant is worth belongs in a public table.
"""

from __future__ import annotations

import csv
from pathlib import Path

from fpm.drafts import split_draft
from fpm.governance.allowlist import host_of
from fpm.kernel import NON_KERNEL_ID, Kernel, load_kernel
from fpm.manifest import FunctionSpec, load_manifest

FUNCTIONS_CSV = Path("data/kernel_functions.csv")
METRICS_CSV = Path("data/kernel_metrics.csv")

FUNCTIONS_COLUMNS = ["kernel_id", "tier", "category", "sub_category", "function", "value"]

METRICS_COLUMNS = [
    "team",
    "function_id",
    "metric",
    "kernel_id",
    "state",
    "origin",
    "grant_ref",
    "oso_project_slug",
    "source_host",
    "repos",
    "cadence",
    "sla_statement",
]

Row = dict[str, str]


def function_rows(kernel: Kernel | None = None) -> list[Row]:
    kernel = load_kernel() if kernel is None else kernel
    return [
        {
            "kernel_id": e.id,
            "tier": e.tier,
            "category": e.category,
            "sub_category": e.sub_category,
            "function": e.function,
            "value": e.value,
        }
        for e in kernel.entries
    ]


def _metric_row(team: str, fn: FunctionSpec, state: str) -> Row:
    return {
        "team": team,
        "function_id": fn.function_id,
        "metric": fn.sla.metric,
        # `non-kernel` is published as itself rather than blanked: the metric is real, it simply
        # evidences nothing the inventory names, and a consumer joining on kernel_id must be able
        # to tell that apart from a missing value.
        "kernel_id": fn.kernel_id,
        "state": state,
        "origin": fn.origin,
        "grant_ref": fn.grant_ref,
        "oso_project_slug": fn.funded_project_oso_slug,
        # `fixture` marks a placeholder awaiting a real feed, which is a different thing from a
        # source whose host we could not parse.
        "source_host": (host_of(fn.source.base_url) or "?")
        if fn.source.kind != "fixture"
        else "fixture",
        "repos": " ".join(sorted(fn.repos)),
        "cadence": fn.sla.cadence,
        "sla_statement": fn.sla.statement,
    }


def metric_rows(
    registry_dir: str | Path = Path("registry"), drafts_dir: str | Path | None = None
) -> list[Row]:
    """One row per SLA entry: every adopted manifest, then every draft.

    A metric declared in BOTH files (how a team proposes its next version) yields two rows, one
    per state, rather than one merged row. Collapsing them would hide either what a team is held
    to today or what it proposes moving to, and a consumer that only wants today's commitments can
    filter `state = 'adopted'`. Rows are sorted so the CSV diff of a registry change is readable.
    """
    registry_dir = Path(registry_dir)
    drafts_dir = registry_dir / "drafts" if drafts_dir is None else Path(drafts_dir)
    rows: list[Row] = []
    for path in sorted(registry_dir.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        m = load_manifest(path)
        rows += [_metric_row(m.team, fn, "adopted") for fn in m.functions]
    if drafts_dir.is_dir():
        for path in sorted(drafts_dir.glob("*.yaml")):
            m, _ = split_draft(path)
            rows += [_metric_row(m.team, fn, "draft") for fn in m.functions]
    return sorted(rows, key=lambda r: (r["team"], r["function_id"], r["metric"], r["state"]))


def unresolved_kernel_ids(rows: list[Row], kernel: Kernel | None = None) -> list[tuple[str, str]]:
    """(team, function_id) whose `kernel_id` names nothing in the inventory.

    The PR gate already rejects this for an adopted manifest, so in practice it catches a draft
    written against a kernel function that has since been renamed. Reported, never dropped: a
    silent drop would understate the metric count exactly where the registry is wrong.
    """
    ids = {e.id for e in (load_kernel() if kernel is None else kernel).entries}
    return [
        (r["team"], r["function_id"])
        for r in rows
        if r["kernel_id"] and r["kernel_id"] != NON_KERNEL_ID and r["kernel_id"] not in ids
    ]


def save_rows(rows: list[Row], columns: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows([{c: row.get(c, "") for c in columns} for row in rows])


def load_rows(path: Path) -> list[Row]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))
