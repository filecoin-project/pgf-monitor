"""The registry is the source of truth for kernel coverage; every published number is derived.

These tests hold two things: the identity rule (a metric counts for the ONE kernel function it
names, not for every function sharing its slot) and the derivation (docs/kernel-coverage.md,
badges.json and the dashboard's embedded payload are exactly what the generator produces from
the current registry — so they cannot drift).
"""

from __future__ import annotations

import ast
import json
from collections import Counter
from pathlib import Path

import pytest

from fpm.kernel import load_kernel
from fpm.manifest import FunctionSpec, SlaSpec, SourceSpec
from scripts.kernel_coverage import (
    BADGES_JSON,
    DASHBOARD,
    EMBED_END,
    EMBED_START,
    OUT,
    badges_data,
    collect,
    counts,
    coverage_json,
    kernel_slots,
    render,
    resolve_kernel_function,
)


def _fn(kernel_function="", tier="irreplaceable", category="", sub_category=""):
    return FunctionSpec(
        function_id="probe",
        kernel_function=kernel_function,
        tier=tier,
        category=category,
        sub_category=sub_category,
        sla=SlaSpec(statement="s", metric="m", cadence="daily"),
        source=SourceSpec(adapter="oso", kind="http-json", base_url="https://api.llama.fi"),
    )


def _a_shared_slot():
    """A (tier, category, sub_category) that several kernel functions live in."""
    for slot, names in kernel_slots(load_kernel()).items():
        if len(names) > 1:
            return slot, names
    pytest.skip("no shared slot in the kernel inventory")


def test_kernel_function_names_are_unique():
    """The generator keys coverage by function NAME, so a duplicate name would silently merge
    two kernel functions into one row."""
    dupes = [n for n, c in Counter(e.function for e in load_kernel().entries).items() if c > 1]
    assert dupes == []


def test_a_named_kernel_function_resolves_to_itself_in_a_shared_slot():
    slot, names = _a_shared_slot()
    fn = _fn(kernel_function=names[1], tier=slot[0], category=slot[1], sub_category=slot[2])
    assert resolve_kernel_function(fn, kernel_slots(load_kernel())) == (names[1], None)


def test_a_shared_slot_without_kernel_function_resolves_to_nothing():
    """This is the bug: keyed on the slot alone, one metric was credited to every function in it,
    which is how 27 covered functions were published as 29/29."""
    slot, names = _a_shared_slot()
    name, why = resolve_kernel_function(
        _fn(tier=slot[0], category=slot[1], sub_category=slot[2]), kernel_slots(load_kernel())
    )
    assert name is None
    assert "kernel_function is unset" in why


def test_a_kernel_function_from_another_slot_is_refused():
    slot, names = _a_shared_slot()
    other = next(
        e.function
        for e in load_kernel().entries
        if (e.tier, e.category, e.sub_category) != slot and e.function not in names
    )
    name, why = resolve_kernel_function(
        _fn(kernel_function=other, tier=slot[0], category=slot[1], sub_category=slot[2]),
        kernel_slots(load_kernel()),
    )
    assert name is None and "is not in slot" in why


def test_every_registry_entry_resolves_to_one_kernel_function():
    """The PR gate already requires this (fpm.kernel.conformance_error), so nothing shipped
    should land in the unresolved bucket."""
    _, _, unresolved = collect()
    assert unresolved == []


def test_an_adopted_metric_is_never_reported_as_a_draft():
    """A draft is how a team proposes its NEXT version; it must not overwrite what is adopted
    today. ankr had two live, passing metrics published as `draft` because both files were
    written into one dict keyed by slot."""
    entries, _, _ = collect()
    adopted = {
        (e["team"], e["function_id"], e["metric"])
        for items in entries.values()
        for e in items
        if e["state"] == "adopted"
    }
    drafted = {
        (e["team"], e["function_id"], e["metric"])
        for items in entries.values()
        for e in items
        if e["state"] == "draft"
    }
    assert adopted & drafted == set()


def test_a_shadowed_adopted_entry_is_flagged_as_having_a_pending_draft():
    entries, _, _ = collect()
    flagged = [
        e for items in entries.values() for e in items if e.get("pending_draft") and e["state"]
    ]
    assert all(e["state"] == "adopted" for e in flagged)


def test_adopted_coverage_never_exceeds_modelled_coverage():
    c = counts(collect()[0], load_kernel())
    assert c["live"] <= c["adopted"] <= c["with_drafts"] <= c["functions"]


def test_committed_coverage_doc_matches_the_registry():
    assert OUT.read_text() == render(), (
        "docs/kernel-coverage.md is stale — regenerate: "
        "uv run python scripts/kernel_coverage.py --write"
    )


def test_committed_badges_match_the_registry():
    assert json.loads(BADGES_JSON.read_text()) == badges_data(), (
        "badges.json is stale — regenerate: uv run python scripts/kernel_coverage.py --badges"
    )


def test_embedded_dashboard_payload_matches_the_registry():
    text = DASHBOARD.read_text()
    body = text[text.index(EMBED_START) + len(EMBED_START) : text.index(EMBED_END)]
    literal = body[body.index("'") : body.rindex("'") + 1]
    assert json.loads(ast.literal_eval(literal)) == coverage_json(), (
        "the dashboard's COVERAGE literal is stale — regenerate: "
        "uv run python scripts/kernel_coverage.py --embed"
    )


def test_the_generator_is_the_only_writer_of_the_derived_artifacts():
    """A reminder in the artifacts themselves, so a hand-edit looks wrong to a reader too."""
    assert "do not edit by hand" in OUT.read_text()
    assert "regenerate it with" in Path("README.md").read_text()
