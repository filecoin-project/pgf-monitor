"""The published page must not be able to go stale quietly.

`published-page.yml` compared only the source hash, so it was blind to the failure it now had to
catch: on 2026-09-20 it passed at 06:52 while the hosted page rendered "as of 2026-09-19" and the
mart had already rebuilt to 09-20. The hash matched because a republish re-renders the SAME source
against NEW data -- so source drift and data staleness are independent, and only one of them was
ever checked.

Fixtures below are the real escaped shapes served from `contentUrl`, not idealised HTML.
"""

from fpm.published_page import (
    RenderedFacts,
    publish_action,
    rendered_facts,
    staleness_problems,
    unescape,
)

# As served: \uXXXX escapes and backslashed quotes inside attributes.
REAL = (
    "Every figure on this page is read from two public tables in the OSO warehouse as of "
    '<span class=\\"mono\\">2026-09-19</span> \\u2014 '
    '<span class=\\"mono\\">kernel_timeseries_metrics_by_project</span> and '
    '<span class=\\"mono\\">kernel_functions</span>. No private source, no embedded snapshot '
    "and no illustrative history: any OSO API key reproduces every one of the "
    "<b>3213</b> daily rows, <b>3207</b> of which carry a value."
)


def test_it_reads_the_pages_own_claims_out_of_the_served_artifact():
    f = rendered_facts(REAL)
    assert (f.as_of, f.rows, f.with_value) == ("2026-09-19", 3213, 3207)


def test_it_reads_plain_html_too():
    """The artifact is escaped; a local render is not. Both must parse."""
    f = rendered_facts(unescape(REAL))
    assert (f.as_of, f.rows, f.with_value) == ("2026-09-19", 3213, 3207)


def test_thousands_separators_do_not_break_the_counts():
    body = REAL.replace("<b>3213</b>", "<b>3,213</b>").replace("<b>3207</b>", "<b>3,207</b>")
    f = rendered_facts(body)
    assert (f.rows, f.with_value) == (3213, 3207)


# ------------------------------------------------------------------ staleness


def test_a_current_page_reports_nothing():
    assert (
        staleness_problems(RenderedFacts("2026-09-20", 3254, 3248), "2026-09-20", 3254, 3248) == []
    )


def test_the_2026_09_20_staleness_is_caught():
    """The exact condition the old hash-only check passed: page a day behind the mart."""
    problems = staleness_problems(RenderedFacts("2026-09-19", 3213, 3207), "2026-09-20", 3254, 3248)
    assert len(problems) == 2
    assert "as of 2026-09-19" in problems[0] and "2026-09-20" in problems[0]
    assert "3213" in problems[1] and "3254" in problems[1]


def test_a_matching_date_with_mismatched_counts_is_still_caught():
    """Same day, different totals -- a partial rebuild, which the date alone would miss."""
    problems = staleness_problems(RenderedFacts("2026-09-20", 3213, 3207), "2026-09-20", 3254, 3248)
    assert len(problems) == 1
    assert "3213" in problems[0]


def test_an_unparseable_page_is_a_problem_not_a_pass():
    """'I could not tell' must never read as 'fine' -- silence is the bug this guards."""
    problems = staleness_problems(RenderedFacts(None, None, None), "2026-09-20", 3254, 3248)
    assert len(problems) == 2
    assert all("could not find" in p for p in problems)
    assert any("_AS_OF" in p for p in problems)
    assert any("_COUNTS" in p for p in problems)


def test_a_reworded_provenance_line_fails_loudly():
    problems = staleness_problems(
        rendered_facts("<p>nothing like the real page</p>"), "2026-09-20", 1, 1
    )
    assert problems


# --------------------------------------------------------------- which action


def test_source_drift_needs_an_upload():
    """force:true re-renders the PLATFORM's stored source, so it cannot fix drift."""
    assert publish_action("aaa", "bbb") == "upload"


def test_a_matching_hash_only_needs_a_data_refresh():
    assert publish_action("aaa", "aaa") == "force"
