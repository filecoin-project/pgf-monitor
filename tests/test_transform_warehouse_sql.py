"""The warehouse-SQL guard: what an `oso-sql` metric may and may not read.

The threat this exists to stop is concrete. The provisioning host's OSO_API_KEY is org-scoped, so
it can read `filpgf_private.*` and `funding_model_static.applicant_identity`. Without a table
allowlist, warehouse SQL in a community PR could put applicant identity into a PUBLIC observation
value. Every rejection below is a way that could have been attempted.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from fpm.transform.validate import (
    TransformSqlError,
    bind_warehouse_sql,
    qualified_tables,
    validate_transform_sql,
    validate_warehouse_sql,
)

ALLOWED = {
    "filecoin.data_portal.daily_filecoin_pay_operators_metrics",
    "filecoin.data_portal.filecoin_pay_rails",
}

# The real metric: FWSS payment volume, which needs a join and so has no shape as a transform.
FWSS_SQL = """
SELECT SUM(m.filecoin_pay_gross_payment_volume_run_rate_usd)
FROM filecoin.data_portal.daily_filecoin_pay_operators_metrics AS m
WHERE m.date = (SELECT MAX(date) FROM filecoin.data_portal.daily_filecoin_pay_operators_metrics)
  AND m.operator IN (
    SELECT DISTINCT operator FROM filecoin.data_portal.filecoin_pay_rails WHERE service = 'FWSS'
  )
"""


def test_accepts_the_two_table_join_the_metric_needs():
    tree = validate_warehouse_sql(FWSS_SQL, ALLOWED)
    assert qualified_tables(tree) == ALLOWED


def test_alias_is_not_part_of_the_table_name():
    """`... AS m` must not leak into the name, or the allowlist check never matches."""
    tree = validate_warehouse_sql(
        "SELECT COUNT(*) FROM filecoin.data_portal.filecoin_pay_rails AS r", ALLOWED
    )
    assert qualified_tables(tree) == {"filecoin.data_portal.filecoin_pay_rails"}


@pytest.mark.parametrize(
    "table",
    [
        "filecoin.filpgf_private.propgf_applications",
        "filecoin.funding_model_static.applicant_identity",
        "filecoin.filpgf_public.kernel_functions",
    ],
)
def test_rejects_any_table_not_on_the_allowlist(table):
    with pytest.raises(TransformSqlError, match="not on the warehouse allowlist"):
        validate_warehouse_sql(f"SELECT COUNT(*) FROM {table}", ALLOWED)


def test_rejects_a_private_table_joined_beside_an_allowlisted_one():
    """The interesting attempt: hide the private read inside an otherwise legitimate query."""
    sql = """
    SELECT MAX(a.applicant_name)
    FROM filecoin.data_portal.filecoin_pay_rails AS r
    JOIN filecoin.funding_model_static.applicant_identity AS a ON a.operator = r.operator
    """
    with pytest.raises(TransformSqlError, match="applicant_identity"):
        validate_warehouse_sql(sql, ALLOWED)


def test_rejects_an_unqualified_table_name():
    """An unqualified name cannot be checked at all, so omission must not be a bypass."""
    with pytest.raises(TransformSqlError, match="fully qualified"):
        validate_warehouse_sql("SELECT COUNT(*) FROM filecoin_pay_rails", ALLOWED)


def test_rejects_a_schema_qualified_but_catalog_less_name():
    with pytest.raises(TransformSqlError, match="fully qualified"):
        validate_warehouse_sql("SELECT COUNT(*) FROM data_portal.filecoin_pay_rails", ALLOWED)


def test_rejects_a_cte_because_its_name_is_unqualified():
    sql = """
    WITH svc AS (SELECT operator FROM filecoin.data_portal.filecoin_pay_rails)
    SELECT COUNT(*) FROM svc
    """
    with pytest.raises(TransformSqlError, match="fully qualified"):
        validate_warehouse_sql(sql, ALLOWED)


def test_rejects_two_statements():
    sql = (
        "SELECT COUNT(*) FROM filecoin.data_portal.filecoin_pay_rails; "
        "SELECT COUNT(*) FROM filecoin.data_portal.filecoin_pay_rails"
    )
    with pytest.raises(TransformSqlError, match="exactly one statement"):
        validate_warehouse_sql(sql, ALLOWED)


def test_rejects_a_non_select_statement():
    with pytest.raises(TransformSqlError, match="only a single SELECT"):
        validate_warehouse_sql("DROP TABLE filecoin.data_portal.filecoin_pay_rails", ALLOWED)


def test_rejects_more_than_one_projection():
    with pytest.raises(TransformSqlError, match="exactly one column"):
        validate_warehouse_sql(
            "SELECT operator, service FROM filecoin.data_portal.filecoin_pay_rails", ALLOWED
        )


def test_rejects_an_unknown_bind_token():
    with pytest.raises(TransformSqlError, match="unknown bind token"):
        validate_warehouse_sql(
            "SELECT COUNT(*) FROM filecoin.data_portal.filecoin_pay_rails WHERE created_at > :nope",
            ALLOWED,
        )


def test_rejects_sql_with_no_table_at_all():
    with pytest.raises(TransformSqlError, match="at least one table"):
        validate_warehouse_sql("SELECT 1", ALLOWED)


def test_empty_allowlist_rejects_everything():
    """A runtime built without the committee list must refuse, not wave everything through."""
    with pytest.raises(TransformSqlError, match="not on the warehouse allowlist"):
        validate_warehouse_sql(FWSS_SQL, set())


def test_allowlist_membership_is_case_insensitive_and_whitespace_tolerant():
    messy = {"  FILECOIN.Data_Portal.Filecoin_Pay_Rails  "}
    validate_warehouse_sql("SELECT COUNT(*) FROM filecoin.data_portal.filecoin_pay_rails", messy)


def test_bind_substitutes_window_tokens_with_owned_literals():
    sql = (
        "SELECT COUNT(*) FROM filecoin.data_portal.filecoin_pay_rails "
        "WHERE created_at >= :window_start_tz AND created_at < :now_tz"
    )
    tree = validate_warehouse_sql(sql, ALLOWED)
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    end = datetime(2026, 9, 10, tzinfo=timezone.utc)
    bound = bind_warehouse_sql(tree, start, end, end)
    assert ":window_start_tz" not in bound and ":now_tz" not in bound
    assert "2026-09-01 00:00:00 +00:00" in bound
    # The table is already real, so binding must leave it exactly as written.
    assert "filecoin.data_portal.filecoin_pay_rails" in bound


def test_the_raw_transform_regime_is_unchanged():
    """The refactor must not have loosened the http-json guard."""
    validate_transform_sql("SELECT COUNT(*) FROM raw")
    with pytest.raises(TransformSqlError, match="only the bound `raw` table"):
        validate_transform_sql("SELECT COUNT(*) FROM filecoin.data_portal.filecoin_pay_rails")


def test_the_two_regimes_do_not_accept_each_other():
    """`raw` is not allowlistable, and a warehouse table is not `raw`."""
    with pytest.raises(TransformSqlError, match="fully qualified"):
        validate_warehouse_sql("SELECT COUNT(*) FROM raw", ALLOWED)


# --- regressions from the 2026-09-11 review: the checked name must BE the executed name ---


@pytest.mark.parametrize(
    "sql",
    [
        # >3 parts: sqlglot's catalog/db/name keep first/second/last, so the middle vanished from
        # the checked string and survived into the executed SQL.
        "SELECT 1 FROM filecoin.data_portal.filpgf_private.filecoin_pay_rails",
        "SELECT 1 FROM filecoin.data_portal.a.b.c.filecoin_pay_rails",
        # dots inside a quoted identifier: re-joins to an allowlisted string, but Trino resolves
        # it against the session default catalog/schema instead.
        'SELECT 1 FROM "filecoin.data_portal".filecoin_pay_rails',
        'SELECT 1 FROM filecoin."data_portal.filecoin_pay_rails"',
        'SELECT 1 FROM "filecoin.data_portal.filecoin_pay_rails"',
    ],
)
def test_a_reference_that_checks_as_allowlisted_but_executes_as_something_else_is_rejected(sql):
    with pytest.raises(TransformSqlError, match="exactly catalog.schema.table"):
        validate_warehouse_sql(sql, ALLOWED)


def test_a_quoted_cte_alias_cannot_impersonate_an_allowlisted_table():
    sql = (
        'WITH "filecoin.data_portal.filecoin_pay_rails" AS (SELECT 1 AS v) '
        'SELECT v FROM "filecoin.data_portal.filecoin_pay_rails"'
    )
    with pytest.raises(TransformSqlError, match="exactly catalog.schema.table"):
        validate_warehouse_sql(sql, ALLOWED)


def test_table_refs_reports_every_part_faithfully():
    """The property the guard rests on: nothing is dropped between checking and executing."""
    from fpm.transform.validate import table_refs

    tree = validate_warehouse_sql(FWSS_SQL, ALLOWED)
    assert all(len(r) == 3 for r in table_refs(tree))
    parsed = __import__("sqlglot").parse_one(
        "SELECT 1 FROM filecoin.data_portal.filpgf_private.filecoin_pay_rails", dialect="trino"
    )
    assert table_refs(parsed) == [
        ("filecoin", "data_portal", "filpgf_private", "filecoin_pay_rails")
    ]


def test_select_star_is_rejected_at_validation_not_left_to_the_adapter():
    """One projection to the parser, any number of columns at runtime — otherwise it becomes a
    permanent `indeterminate` that both static gates call fine."""
    with pytest.raises(TransformSqlError, match="not a single scalar"):
        validate_warehouse_sql("SELECT * FROM filecoin.data_portal.filecoin_pay_rails", ALLOWED)


def test_select_star_is_rejected_in_the_raw_transform_regime_too():
    with pytest.raises(TransformSqlError, match="not a single scalar"):
        validate_transform_sql("SELECT * FROM raw")
