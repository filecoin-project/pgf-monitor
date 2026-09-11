"""Manifest rules for the `oso-sql` kind.

Each rejection below exists so a reader of `registry/<team>.yaml` can tell, without running
anything, exactly where an entry's number comes from. An entry that declares both a fetch and a
warehouse read, or both a `sql` and an `extract`, leaves that ambiguous.
"""

from __future__ import annotations

import copy

import pytest
import yaml

from fpm.manifest import ManifestError, manifest_from_raw

BASE = yaml.safe_load(open("tests/fixtures/filoz_oso_sql.yaml").read())


def _raw(**source_overrides):
    raw = copy.deepcopy(BASE)
    raw["functions"][0]["source"].update(source_overrides)
    return raw


def test_the_fixture_is_valid():
    m = manifest_from_raw(copy.deepcopy(BASE))
    assert m.functions[0].source.kind == "oso-sql"
    assert "filecoin_pay_rails" in m.functions[0].source.sql


def test_sql_survives_the_round_trip_into_the_model():
    """The whole derivation lives in this field; silently dropping it would measure nothing."""
    m = manifest_from_raw(copy.deepcopy(BASE))
    assert m.functions[0].source.sql.strip().startswith("SELECT SUM(")


def test_missing_sql_is_rejected():
    """Rejected twice over: _schema.json requires it for this kind, and manifest_from_raw checks
    again. The schema speaks first, which is why the message is its wording and not ours."""
    raw = _raw()
    del raw["functions"][0]["source"]["sql"]
    with pytest.raises(ManifestError, match="'sql' is a required property"):
        manifest_from_raw(raw)


def test_blank_sql_is_rejected():
    # The schema's minLength catches an empty string; a whitespace-only one reaches our check.
    with pytest.raises(ManifestError):
        manifest_from_raw(_raw(sql="   \n  "))


def test_declaring_an_extract_beside_sql_is_rejected():
    raw = _raw(extract={"column": "x"})
    with pytest.raises(ManifestError, match="source.sql is the whole derivation"):
        manifest_from_raw(raw)


def test_declaring_a_transform_beside_sql_is_rejected():
    raw = copy.deepcopy(BASE)
    raw["functions"][0]["transform"] = {"sql": "SELECT COUNT(*) FROM raw"}
    with pytest.raises(ManifestError, match="source.sql is the whole derivation"):
        manifest_from_raw(raw)


@pytest.mark.parametrize(
    "field,value",
    [
        ("base_url", "https://api.github.com"),
        ("endpoint", "https://api.github.com/x"),
        ("query", "/x"),
        ("params", {"a": "b"}),
    ],
)
def test_fetch_fields_are_rejected_because_nothing_is_fetched(field, value):
    """base_url especially: it is what the egress host allowlist is checked against, so an
    oso-sql entry carrying one would imply a host review that never happens."""
    with pytest.raises(ManifestError, match="performs no HTTP fetch"):
        manifest_from_raw(_raw(**{field: value}))


def test_an_http_json_entry_may_still_not_omit_its_derivation():
    """Guard against the new branch accidentally short-circuiting the http-json rule."""
    raw = copy.deepcopy(BASE)
    src = raw["functions"][0]["source"]
    src.pop("sql")
    src.update(adapter="oso", kind="http-json", base_url="https://api.github.com", query="/x")
    with pytest.raises(ManifestError, match="needs exactly one of source.extract or transform"):
        manifest_from_raw(raw)


def test_source_sql_is_classified_as_material():
    """An unclassified field would escape both the goalpost diff and the live dry-run."""
    from fpm.governance.fields import bucket_for, unclassified_field_paths

    assert bucket_for("source.sql") == "material"
    assert unclassified_field_paths() == set()


def test_changing_the_sql_registers_as_a_changed_field():
    from fpm.governance.fields import changed_field_paths

    old = manifest_from_raw(copy.deepcopy(BASE)).functions[0]
    new = manifest_from_raw(
        _raw(sql="SELECT COUNT(*) FROM filecoin.data_portal.filecoin_pay_rails")
    ).functions[0]
    assert "source.sql" in changed_field_paths(old, new)


def test_kind_and_adapter_must_agree_or_the_gates_check_the_wrong_derivation():
    """The static gates branch on `kind`; `measure` dispatches on `adapter`. If they disagree the
    committee approves and dry-runs an http-json fetch while the nightly runs source.sql."""
    raw = _raw(
        kind="http-json",
        base_url="https://api.github.com",
        query="/x",
        endpoint="https://api.github.com/x",
    )
    raw["functions"][0]["source"]["adapter"] = "oso-sql"
    with pytest.raises(ManifestError, match="must be both or neither"):
        manifest_from_raw(raw)


def test_the_mismatch_is_rejected_in_the_other_direction_too():
    raw = _raw()
    raw["functions"][0]["source"]["adapter"] = "oso"
    with pytest.raises(ManifestError, match="must be both or neither"):
        manifest_from_raw(raw)
