"""A manifest field is SEMANTIC until someone says otherwise, and the diff is the only list.

The diff used to enumerate the fields it compared by hand, so three fields the models grew were
never compared: `team`, `kernel_function` and `source.data_selector`. `data_selector` is the
dangerous one — it decides which part of a JSON response is read, so changing it changes the
measured value, and because the live dry-run only runs over functions the diff calls changed, a
`data_selector`-only PR moved the goalposts with no warning and no live proof.
"""

from __future__ import annotations

from fpm.governance.classify import classify
from fpm.governance.diff import manifest_diff
from fpm.governance.fields import (
    FIELD_BUCKETS,
    changed_field_paths,
    manifest_field_paths,
    unclassified_field_paths,
)
from fpm.manifest import load_manifest
from scripts.dry_run_pr import changed_function_ids

FIXTURE = "tests/fixtures/chainsafe_oso.yaml"


def _with_function(**kw):
    m = load_manifest(FIXTURE)
    m2 = m.model_copy(deep=True)
    for k, v in kw.items():
        target, _, attr = k.rpartition(".")
        obj = m2.functions[0]
        for part in filter(None, target.split(".")):
            obj = getattr(obj, part)
        setattr(obj, attr, v)
    return m, m2


def test_every_manifest_field_is_classified():
    """Fail closed: a field added to the models without a bucket breaks this test, rather than
    silently dropping out of goalpost detection and out of dry-run selection."""
    missing = unclassified_field_paths()
    assert missing == set(), (
        f"unclassified manifest field(s): {sorted(missing)} — add each to "
        "fpm.governance.fields.FIELD_BUCKETS as 'material' or, only if a change provably cannot "
        "alter what is measured, how the number is read, or who is accountable, 'trivial'"
    )


def test_no_bucket_is_claimed_for_a_field_that_does_not_exist():
    assert set(FIELD_BUCKETS) - manifest_field_paths() == set()


def test_trivial_is_a_short_explicit_list():
    """Trivial is the exception and must stay boring. If this list grows, argue for it."""
    trivial = {p for p, b in FIELD_BUCKETS.items() if b == "trivial"}
    assert trivial == {"sla.statement", "maintainers"}


def test_data_selector_is_diffed_and_material():
    m, m2 = _with_function(**{"source.data_selector": "result.deeper"})
    changes = manifest_diff(m, m2)
    assert any(c.field_path == "source.data_selector" for c in changes), (
        "a data_selector change reads a different part of the response — it cannot be invisible"
    )
    classified = classify(changes, m2)
    assert any(
        c.field_path == "source.data_selector" and c.bucket == "material" for c in classified
    )


def test_kernel_function_is_diffed():
    m, m2 = _with_function(kernel_function="Chain ETL and indexing")
    assert any(c.field_path == "kernel_function" for c in manifest_diff(m, m2))


def test_team_is_diffed():
    m = load_manifest(FIXTURE)
    m2 = m.model_copy(deep=True)
    m2.team = "someone-else"
    assert any(c.field_path == "team" for c in manifest_diff(m, m2))


def test_a_team_change_marks_every_function_changed():
    """`team` is part of the dataset name and of every observation and threshold row's key, so
    renaming it re-points every measurement the manifest makes."""
    m = load_manifest(FIXTURE)
    m2 = m.model_copy(deep=True)
    m2.team = "someone-else"
    assert changed_function_ids(m, m2) == {f.function_id for f in m2.functions}


def test_the_dry_run_selects_exactly_the_semantically_changed_functions():
    m, m2 = _with_function(**{"source.data_selector": "result.deeper"})
    assert changed_function_ids(m, m2) == {m2.functions[0].function_id}


def test_changed_field_paths_reports_the_paths_that_differ():
    m, m2 = _with_function(**{"source.data_selector": "x"})
    assert "source.data_selector" in changed_field_paths(m.functions[0], m2.functions[0])
