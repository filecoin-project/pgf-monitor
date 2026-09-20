"""Republish the public dashboard, then prove it landed.

Publishing was manual, and manual lost twice in one afternoon on 2026-09-14 and again on
2026-09-20. The failure is always silent in the same way: a stale page is a working page, so
nothing errors and nobody notices by looking.

**Two independent faults, two different fixes, and they are not interchangeable.**

- SOURCE drift -- a notebook change merged to main and never republished. Fixed only by uploading
  the file: `publishNotebook(force:true)` re-renders the PLATFORM's stored source and would
  happily republish the old build forever.
- DATA staleness -- the mart gained a day while the source stayed put. A published notebook
  renders whatever it queried into a static page, so the hash still matches and the numbers are
  old. Fixed by `publishNotebook(force:true)`; `force` is required precisely BECAUSE the source
  is unchanged, or the publish is skipped on the source hash.

`fpm.published_page.publish_action` picks between them, so an upload happens only when the source
actually drifted and the daily refresh does not mint a notebook revision every morning.

Run FROM a checkout of main. That is the whole point: republishing from a checkout makes
"hosted == main" true by construction, where anything working from the platform's own copy can
only ever observe drift.

Live network, so it is quarantined like the smokes and no test imports it; the decisions it makes
live in `fpm.published_page`, which is tested offline.

    OSO_API_KEY=... uv run python scripts/publish_page.py [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from fpm.published_page import publish_action

NOTEBOOK = Path("dashboards/propgf-kernel-public.py")
ORG = "filecoin"
NAME = "propgf-kernel-health-live"
NOTEBOOK_ID = "1192c8f0-c6ad-44c5-83ba-fa8f6b4ed803"
ORG_ID = "35c17c26-4aa8-47ba-ba75-be8fe1e3718c"
API = "https://api.oso.xyz/v1/graphql"

#: Observed ~60s for a publish to reach READY; 5 minutes is generous without hanging a job.
POLL_ATTEMPTS, POLL_SLEEP = 30, 10


def gql(key: str, query: str, variables: dict | None = None) -> dict:
    """POST to the OSO GraphQL API. curl, not urllib: Cloudflare 403s python-urllib outright."""
    payload = {"query": query}
    if variables is not None:
        payload["variables"] = variables
    out = subprocess.run(
        ["curl", "-sS", "--max-time", "120", API,
         "-H", f"Authorization: Bearer {key}",
         "-H", "Content-Type: application/json",
         "-H", "User-Agent: fpm-publish-page/1.0",
         "--data-binary", json.dumps(payload)],
        capture_output=True, text=True, timeout=180,
    )  # fmt: skip
    body = json.loads(out.stdout or "{}")
    if body.get("errors"):
        raise SystemExit(f"GraphQL error: {json.dumps(body['errors'])[:600]}")
    return body.get("data") or {}


def hosted(key: str) -> dict:
    q = (
        '{ publishedNotebookByName(orgName:"%s", notebookName:"%s")'
        "{ status sourceHash errorMessage } }" % (ORG, NAME)
    )
    return gql(key, q).get("publishedNotebookByName") or {}


def upload_source(key: str) -> None:
    """Replace the platform's stored notebook with main's copy. `updateNotebook` auto-publishes."""
    up = gql(
        key,
        "mutation($orgId:ID!){ createNotebookUploadUrl(orgId:$orgId){ uploadUrl uploadId } }",
        {"orgId": ORG_ID},
    )["createNotebookUploadUrl"]
    put = subprocess.run(
        ["curl", "-sS", "-o", os.devnull, "-w", "%{http_code}", "--max-time", "120",
         "-X", "PUT", "--data-binary", f"@{NOTEBOOK}", up["uploadUrl"]],
        capture_output=True, text=True, timeout=180,
    )  # fmt: skip
    if put.stdout.strip() != "200":
        raise SystemExit(f"upload PUT returned HTTP {put.stdout.strip()}")
    gql(
        key,
        "mutation($input:UpdateNotebookInput!){ updateNotebook(input:$input){ success } }",
        {"input": {"id": NOTEBOOK_ID, "uploadId": up["uploadId"]}},
    )


def force_publish(key: str) -> None:
    """Re-render the stored source against current data. `force` because the source is unchanged."""
    gql(
        key,
        "mutation($notebookId:ID!,$force:Boolean){ publishNotebook(notebookId:$notebookId, "
        "force:$force){ success message } }",
        {"notebookId": NOTEBOOK_ID, "force": True},
    )


def wait_ready(key: str) -> dict:
    """Poll by NAME: `notebookByName{publishedNotebook}` goes null mid-publish, this does not."""
    node: dict = {}
    for _ in range(POLL_ATTEMPTS):
        node = hosted(key)
        if node.get("status") in {"READY", "FAILED"}:
            return node
        time.sleep(POLL_SLEEP)
    return node


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dry-run", action="store_true", help="say what would be published, publish nothing"
    )
    args = ap.parse_args(argv)

    key = os.environ.get("OSO_API_KEY", "")
    if not key:
        print("OSO_API_KEY is not set; cannot publish", file=sys.stderr)
        return 1

    local = hashlib.sha256(NOTEBOOK.read_bytes()).hexdigest()
    before = hosted(key)
    action = publish_action(local, before.get("sourceHash", ""))
    print(f"local {local[:16]}  hosted {str(before.get('sourceHash'))[:16]}  -> {action}")

    if args.dry_run:
        print("dry run: nothing published")
        return 0

    if action == "upload":
        upload_source(key)
    else:
        force_publish(key)

    node = wait_ready(key)
    if node.get("status") != "READY":
        print(
            f"publish did not reach READY: status={node.get('status')!r} "
            f"error={node.get('errorMessage')!r}",
            file=sys.stderr,
        )
        return 1
    if node.get("sourceHash") != local:
        print(
            f"published, but the hosted hash {node.get('sourceHash')} still does not match main "
            f"({local}) -- a `force` refresh cannot replace the stored source",
            file=sys.stderr,
        )
        return 1

    print(f"published ({action}); verifying what the reader actually gets")
    # Deliberately the SAME check the scheduled guard runs, not a weaker inline copy: a publish
    # that cannot pass the guard is not a publish worth reporting as success.
    return subprocess.run([sys.executable, "-m", "scripts.check_published_page"]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
