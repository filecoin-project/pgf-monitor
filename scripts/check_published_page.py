"""Does the page people read still match what is on main?

Publishing the public dashboard is MANUAL. Merging a change to
`dashboards/propgf-kernel-public.py` does not touch the hosted notebook -- someone has to
republish it. That gap is silent, and it caught this repo twice in one afternoon on 2026-09-14:
a rendering fix and a comment change each sat on main while the live page served the old build.

Nobody notices drift by looking, because a stale page is a working page. So check it, and check
the two things that actually matter to a reader:

  1. the hosted source hash equals sha256 of the file on main -- `publishedNotebookByName.sourceHash`
     IS a plain sha256 of the bytes, verified 2026-09-14, so this needs no download;
  2. the page is reachable WITHOUT an account at its /view URL. The bare
     /filecoin/propgf-kernel-health-live path 307s to /login, which is how a link in README and
     SKILL.md pointed somewhere useless for weeks without erroring.

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

NOTEBOOK = Path("dashboards/propgf-kernel-public.py")
ORG = "filecoin"
NAME = "propgf-kernel-health-live"
VIEW = f"https://www.oso.xyz/{ORG}/{NAME}/view"
API = "https://api.oso.xyz/v1/graphql"

QUERY = (
    '{ publishedNotebookByName(orgName:"%s", notebookName:"%s")'
    "{ status sourceHash updatedAt errorMessage } }" % (ORG, NAME)
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
            "the hosted page does NOT match main. Republish it -- see dashboards/README.md; "
            "nothing does this automatically."
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

    if problems:
        for p in problems:
            print(f"FAIL: {p}", file=sys.stderr)
        return 1
    print("OK: the published page matches main and is publicly readable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
