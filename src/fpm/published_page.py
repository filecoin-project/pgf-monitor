"""What the hosted page claims, and whether it still agrees with the warehouse.

The pure half of the published-page guard. Network I/O lives in `scripts/check_published_page.py`
and `scripts/publish_page.py`, which are quarantined the way the live smokes are; everything here
is string-in, verdict-out so it can be tested offline.

**Why a hash check is not enough.** `published-page.yml` compared `publishedNotebookByName
.sourceHash` against sha256 of the file on main, and nothing else. That catches SOURCE drift --
a notebook change merged and never republished, which is what it was built for on 2026-09-14 --
and is structurally blind to DATA staleness. A published notebook renders whatever it queried
into a static page, so once the mart gains a day the page keeps serving the old numbers under an
unchanged hash. On 2026-09-20 the check passed at 06:52 while the page said "as of 2026-09-19"
and the mart had already rebuilt to 09-20. A stale page is a working page; nobody notices by
looking.

So the page is asked what it thinks it knows. It states both facts in its own provenance line:

    ...in the OSO warehouse as of <span class="mono">2026-09-19</span> ... any OSO API key
    reproduces every one of the <b>3213</b> daily rows, <b>3207</b> of which carry a value.

Those come from the notebook's own `n_rows` / `n_read` over an UNFILTERED
`SELECT ... FROM kernel_timeseries_metrics_by_project`, so they are comparable to a plain
COUNT(*) on that table rather than coincidentally equal to one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: The published artifact is heavily escaped -- `\uXXXX` for punctuation and backslashed quotes
#: inside attributes -- so every pattern here tolerates both forms rather than assuming raw HTML.
_AS_OF = re.compile(r"warehouse as of\s*<span[^>]*>\s*(\d{4}-\d{2}-\d{2})\s*</span>")
_COUNTS = re.compile(r"<b>([\d,]+)</b>\s*daily rows,\s*<b>([\d,]+)</b>\s*of which carry a value")


def unescape(body: str) -> str:
    """Decode the `\\uXXXX` escapes the published artifact is served with."""
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), body)


@dataclass(frozen=True)
class RenderedFacts:
    """What the page says about itself. Any field may be None if the page changed shape."""

    as_of: str | None
    rows: int | None
    with_value: int | None


def rendered_facts(body: str) -> RenderedFacts:
    """Pull the page's own provenance claims out of the published HTML."""
    text = unescape(body)
    as_of = m.group(1) if (m := _AS_OF.search(text)) else None
    if m := _COUNTS.search(text):
        return RenderedFacts(
            as_of, int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
        )
    return RenderedFacts(as_of, None, None)


def staleness_problems(
    page: RenderedFacts, mart_latest: str, mart_rows: int, mart_with_value: int
) -> list[str]:
    """Where the page and the warehouse disagree. Empty means the page is current.

    A page that cannot be parsed is reported rather than passed: the failure mode this exists to
    prevent is a silent one, so "I could not tell" must not read as "fine". If the provenance
    line is ever reworded, this fires and the wording and the regex get reconciled -- noisy in
    exactly the situation where silence was the original bug.
    """
    problems: list[str] = []

    if page.as_of is None:
        problems.append(
            "could not find the 'as of <date>' provenance line in the published page -- "
            "if it was reworded, update fpm.published_page._AS_OF to match"
        )
    elif page.as_of != mart_latest:
        problems.append(
            f"the page renders data as of {page.as_of} but the mart's latest sample_date is "
            f"{mart_latest}. The hash still matches because a republish re-renders the SAME "
            f"source against NEW data -- republish it (scripts/publish_page.py)"
        )

    if page.rows is None or page.with_value is None:
        problems.append(
            "could not find the '<b>N</b> daily rows' provenance counts in the published page -- "
            "if that sentence was reworded, update fpm.published_page._COUNTS to match"
        )
    elif (page.rows, page.with_value) != (mart_rows, mart_with_value):
        problems.append(
            f"the page claims {page.rows} daily rows ({page.with_value} with a value) but the "
            f"mart holds {mart_rows} ({mart_with_value} with a value)"
        )

    return problems


def publish_action(local_hash: str, hosted_hash: str) -> str:
    """Which republish the page needs: `upload` when the source drifted, `force` otherwise.

    The two are not interchangeable, and picking the wrong one silently does nothing useful.
    `publishNotebook(force:true)` re-renders the PLATFORM's stored source, so it refreshes data
    and cannot fix source drift. Uploading the file and calling `updateNotebook` replaces the
    stored source and republishes, fixing both -- at the cost of a new revision every time, which
    is why it is not simply done unconditionally.
    """
    return "upload" if local_hash != hosted_hash else "force"
