"""The outage policy and the documents that promise it must not drift apart.

`PLATFORM_OUTAGES` in dashboards/propgf-kernel-public.py decides which days leave every coverage
denominator on the public page. Two documents make that same promise to people who never read the
notebook:

- `docs/public-datasets.md` is the CONSUMER CONTRACT. It tells an outside reader building their
  own coverage number which dates to exclude. A date excluded on our page but absent there means
  we publish a number nobody else can reproduce, and the team it protects is protected only on
  our page.
- `dashboards/README.md` states the policy for anyone working on the dashboard.

Adding an outage date is three edits and it is easy to make one. This is the test that catches
the other two -- an assertion about documentation, deliberately, because the documentation is the
part with real consequences for someone downstream.
"""

import re
from pathlib import Path

NOTEBOOK = Path("dashboards/propgf-kernel-public.py")
CONTRACT = Path("docs/public-datasets.md")
DASH_README = Path("dashboards/README.md")


def outage_dates() -> set[str]:
    """The dates in the notebook's PLATFORM_OUTAGES literal.

    Parsed rather than imported: the notebook is a marimo app whose import pulls in the dashboard
    extra, which the default test environment does not install.
    """
    body = NOTEBOOK.read_text()
    match = re.search(r"PLATFORM_OUTAGES\s*=\s*\{([^}]*)\}", body)
    assert match, "PLATFORM_OUTAGES literal not found in the notebook"
    return set(re.findall(r"\d{4}-\d{2}-\d{2}", match.group(1)))


def test_the_policy_carries_the_dates_we_expect():
    """A canary on the set itself: a date added or dropped should be a deliberate edit here too."""
    assert outage_dates() == {"2026-08-22", "2026-08-23", "2026-09-18"}


def test_every_outage_date_is_named_in_the_consumer_contract():
    """docs/public-datasets.md tells outside consumers which dates to drop from their own
    denominators. A date missing there is a coverage number nobody can reproduce."""
    body = CONTRACT.read_text()
    missing = sorted(d for d in outage_dates() if d not in body)
    assert not missing, f"{CONTRACT} does not name outage date(s): {', '.join(missing)}"


def test_every_outage_date_is_named_in_the_dashboard_readme():
    body = DASH_README.read_text()
    missing = sorted(d for d in outage_dates() if d not in body)
    assert not missing, f"{DASH_README} does not name outage date(s): {', '.join(missing)}"


def test_an_outage_date_is_never_before_coverage_starts():
    """Excluding a day earlier than COVERAGE_FROM is a no-op that reads as protection."""
    match = re.search(r'COVERAGE_FROM\s*=\s*"(\d{4}-\d{2}-\d{2})"', NOTEBOOK.read_text())
    assert match
    assert all(d >= match.group(1) for d in outage_dates())
