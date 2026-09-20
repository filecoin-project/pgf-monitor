"""Does the page people read still match what is on main?

Publishing is automatic since 2026-09-20 (`published-page.yml` -> `scripts/publish_page.py`),
so this is now the PROOF rather than the alarm -- the publish step ends by running it, and a
publish that cannot pass it is not reported as success. It still runs on its own daily, because
the page can go wrong without anyone publishing: the mart rebuilds underneath it.

It was written when publishing was manual, and manual lost twice in one afternoon on 2026-09-14:
a rendering fix and a comment change each sat on main while the live page served the old build.

Nobody notices drift by looking, because a stale page is a working page. So check it, and check
the two things that actually matter to a reader:

  1. the hosted source hash equals sha256 of the file on main -- `publishedNotebookByName.sourceHash`
     IS a plain sha256 of the bytes, verified 2026-09-14, so this needs no download;
  2. the page is reachable WITHOUT an account at its /view URL. The bare
     /filecoin/propgf-kernel-health-live path 307s to /login, which is how a link in README and
     SKILL.md pointed somewhere useless for weeks without erroring;
  3. the DATA it rendered still matches the warehouse. A hash check cannot see this: a published
     notebook renders whatever it queried into a static page, so once the mart gains a day the
     page serves the old numbers under an unchanged hash. That is exactly what happened on
     2026-09-20 -- this check passed at 06:52 while the page said "as of 2026-09-19" and the mart
     had rebuilt to 09-20. Source drift and data staleness are independent faults.

Live network, so it is quarantined like the smokes and no test imports it.

    uv run python scripts/check_published_page.py        # exits 1 on drift
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from fpm.published_page import rendered_facts, staleness_problems

NOTEBOOK = Path("dashboards/propgf-kernel-public.py")
ORG = "filecoin"
NAME = "propgf-kernel-health-live"
VIEW = f"https://www.oso.xyz/{ORG}/{NAME}/view"
API = "https://api.oso.xyz/v1/graphql"

QUERY = (
    '{ publishedNotebookByName(orgName:"%s", notebookName:"%s")'
    "{ status sourceHash updatedAt errorMessage contentUrl } }" % (ORG, NAME)
)


def _post(api_key: str) -> dict:
    out = subprocess.run(
        [
            "curl",
            "-sS",
            "--max-time",
            "30",
            API,
            "-H",
            f"Authorization: Bearer {api_key}",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps({"query": QUERY}),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return json.loads(out.stdout)


def _mart_totals() -> tuple[str, int, int]:
    """The warehouse's own view of the table the page reads. Unfiltered, like the page's query."""
    from pyoso import Client

    row = (
        Client()
        .to_pandas(
            "SELECT CAST(MAX(sample_date) AS VARCHAR) AS latest, COUNT(*) AS rows, "
            "COUNT(amount) AS with_value "
            "FROM filecoin.filpgf_public.kernel_timeseries_metrics_by_project"
        )
        .to_dict("records")[0]
    )
    return str(row["latest"]), int(row["rows"]), int(row["with_value"])


def _fetch(url: str) -> str:
    out = subprocess.run(
        ["curl", "-sS", "--compressed", "--max-time", "60", url],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return out.stdout


def main(argv=None) -> int:
    key = os.environ.get("OSO_API_KEY", "")
    if not key:
        print("OSO_API_KEY is not set; cannot check the hosted page", file=sys.stderr)
        return 1

    local = hashlib.sha256(NOTEBOOK.read_bytes()).hexdigest()
    payload = _post(key)
    node = (payload.get("data") or {}).get("publishedNotebookByName") or {}
    if not node:
        print(
            f"could not read the published notebook: {json.dumps(payload)[:400]}", file=sys.stderr
        )
        return 1

    hosted, status = node.get("sourceHash", ""), node.get("status", "")
    print(f"local  {local}\nhosted {hosted}\nstatus {status}  updated {node.get('updatedAt')}")

    problems = []
    if status != "READY":
        problems.append(f"published status is {status!r}, not READY ({node.get('errorMessage')})")
    if hosted != local:
        problems.append(
            "the hosted page does NOT match main. CI republishes on push and daily; if this "
            "fires, that did not happen or it failed -- run scripts/publish_page.py."
        )

    # Anonymous reachability: no API key, no cookies. This is the reader's experience.
    code = subprocess.run(
        ["curl", "-sS", "-o", os.devnull, "-w", "%{http_code}", "--max-time", "30", VIEW],
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout.strip()
    print(f"anonymous {VIEW} -> HTTP {code}")
    if code != "200":
        problems.append(f"{VIEW} is not anonymously readable (HTTP {code})")

    # Does the page still render what the warehouse holds? Independent of the hash above, and
    # the half that was missing: a republish re-renders the SAME source against NEW data.
    content_url = node.get("contentUrl")
    if not content_url:
        problems.append("the published notebook reports no contentUrl; cannot check its data")
    else:
        facts = rendered_facts(_fetch(content_url))
        latest, rows, with_value = _mart_totals()
        print(
            f"page     as of {facts.as_of}  rows {facts.rows}  with value {facts.with_value}\n"
            f"mart     as of {latest}  rows {rows}  with value {with_value}"
        )
        problems.extend(staleness_problems(facts, latest, rows, with_value))

    if problems:
        for p in problems:
            print(f"FAIL: {p}", file=sys.stderr)
        return 1
    print("OK: the published page matches main, renders current data, and is publicly readable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
