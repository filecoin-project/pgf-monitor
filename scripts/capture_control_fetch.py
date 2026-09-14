"""Ask GitHub the same question OSO just asked, from here, seconds later.

`fpm observe` refuses an age reading it can prove false and writes what produced it to
`evidence/refused-readings/` (fpm.guards). That capture answers WHAT came back. It cannot answer
WHERE the stale page came from, because the fetch was made by OSO's ingestion on OSO's network
path, and the only thing we hold afterwards is the rows it stored.

This closes that gap. For each capture, it repeats the request DIRECTLY -- different client,
different network path, same instant -- and records the answer with GitHub's own response headers.
The next occurrence then splits three ways instead of staying ambiguous:

    control FRESH, OSO stale   -> the fault is on OSO's path to GitHub, not GitHub itself
    control STALE too          -> GitHub is serving it, and `x-github-request-id` makes it
                                  reportable to them, which nothing we hold today does
    control fresh AND filtered
      variant stale            -> the `status=success` index specifically, which is the theory
                                  the 2026-09-14 fix was built on but never proved

That last one matters: the manifest moved off `?status=success` on the strength of a mechanism,
not a controlled comparison. This fetches BOTH shapes every time, so the claim gets tested rather
than assumed.

Never fails a run. It is evidence collection attached to a failure that has already happened;
turning a diagnostic into a second failure would be the wrong trade. Live network, so it is
quarantined here and never imported by tests.

Usage (the observe workflow runs it between the guard and the artifact upload):
    uv run python scripts/capture_control_fetch.py [--dir evidence/refused-readings]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

#: Headers worth keeping. `x-github-request-id` is the one GitHub support can act on; `age` and
#: the cache headers say whether anything between us and them admits to holding a copy.
HEADERS = (
    "date",
    "age",
    "cache-control",
    "etag",
    "last-modified",
    "x-github-request-id",
    "x-ratelimit-remaining",
    "server",
    "via",
    "x-served-by",
    "cf-cache-status",
)


def _curl(url: str, token: str = "") -> dict:
    """GET a URL, returning status, selected headers and body. Cloudflare blocks python-urllib."""
    cmd = ["curl", "-sS", "-D", "-", "--max-time", "30"]
    if token:
        cmd += ["-H", f"Authorization: Bearer {token}"]
    cmd.append(url)
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except Exception as exc:  # pragma: no cover - live path
        return {"url": url, "error": f"{type(exc).__name__}: {exc}"}
    raw = out.stdout
    head, _, body = raw.partition("\r\n\r\n")
    if not body:
        head, _, body = raw.partition("\n\n")
    status = ""
    headers = {}
    for line in head.splitlines():
        if line.lower().startswith("http/"):
            status = line.strip()
        elif ":" in line:
            k, v = line.split(":", 1)
            if k.strip().lower() in HEADERS:
                headers[k.strip().lower()] = v.strip()
    rec = {"url": url, "status": status, "headers": headers}
    if out.stderr.strip():
        rec["stderr"] = out.stderr.strip()[:400]
    try:
        rec["body"] = json.loads(body)
    except Exception:
        rec["body_text"] = body[:400]
    return rec


def _runs_summary(payload: dict) -> dict:
    """The few facts that decide fresh-vs-stale, without keeping a megabyte of run JSON."""
    runs = (payload or {}).get("workflow_runs") or []
    picked = [
        {
            "run_number": r.get("run_number"),
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"),
            "status": r.get("status"),
            "conclusion": r.get("conclusion"),
        }
        for r in runs[:10]
    ]
    ok = [r for r in runs if r.get("status") == "completed" and r.get("conclusion") == "success"]
    return {
        "total_count": (payload or {}).get("total_count"),
        "returned": len(runs),
        "newest_success_updated_at": max((r.get("updated_at") or "" for r in ok), default=None),
        "runs": picked,
    }


def _filtered_variant(url: str) -> str:
    """The same URL with `status=success` put back -- the shape blamed for every episode."""
    u = urlparse(url)
    q = [p for p in u.query.split("&") if p and not p.startswith("status=")]
    return urlunparse(u._replace(query="&".join(["status=success", *q])))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="evidence/refused-readings")
    ap.add_argument("--token-env", default="GH_API_TOKEN")
    args = ap.parse_args(argv)

    import os

    token = os.environ.get(args.token_env, "")
    captures = sorted(Path(args.dir).glob("*.json")) if Path(args.dir).is_dir() else []
    if not captures:
        print("no refused readings to follow up -- nothing to do")
        return 0

    for path in captures:
        try:
            rec = json.loads(path.read_text())
        except Exception as exc:
            print(f"  {path.name}: unreadable ({exc})", file=sys.stderr)
            continue
        endpoint = rec.get("endpoint") or ""
        if not endpoint.startswith("http"):
            print(f"  {path.name}: no endpoint recorded, skipping")
            continue

        control = {"fetched_at": datetime.now(timezone.utc).isoformat()}
        # Authenticated, exactly as the nightly asks it.
        control["as_asked"] = _curl(endpoint, token)
        # The same question with the filter restored, to test the theory the fix rests on.
        control["filtered_variant"] = _curl(_filtered_variant(endpoint), token)
        # Unauthenticated: a different cache key entirely, and it costs one of 60/hour.
        control["unauthenticated"] = _curl(endpoint)

        for k in ("as_asked", "filtered_variant", "unauthenticated"):
            body = control[k].pop("body", None)
            if body is not None:
                control[k]["summary"] = _runs_summary(body)

        rec["control_fetch"] = control
        # What the refused reading implied, so the comparison is readable without arithmetic.
        rec["control_verdict"] = _verdict(rec, control)
        path.write_text(json.dumps(rec, indent=2, default=str) + "\n")
        print(f"  {path.name}: control fetch recorded -> {rec['control_verdict']}")
    return 0


def _verdict(rec: dict, control: dict) -> str:
    """A one-line reading of the comparison, for whoever opens the artifact first."""
    stored = rec.get("rows") or []
    stored_newest = max(
        (str(r.get("updated_at") or r.get("created_at") or "") for r in stored), default=""
    )
    live = (control.get("as_asked", {}).get("summary") or {}).get("newest_success_updated_at") or ""
    filt = (control.get("filtered_variant", {}).get("summary") or {}).get(
        "newest_success_updated_at"
    ) or ""
    if not live:
        return "control fetch failed; no comparison possible"
    if stored_newest and stored_newest[:10] == live[:10]:
        return "control agrees with what OSO stored -- the staleness is NOT reproducible from here"
    if filt and filt[:10] != live[:10]:
        return (
            f"SPLIT: unfiltered newest {live[:10]}, filtered newest {filt[:10]} -- "
            "the status=success index is behind, which is the theory the fix rests on"
        )
    return (
        f"control is FRESH ({live[:10]}) while OSO stored {stored_newest[:10] or 'nothing dated'} "
        "-- the stale page did not come from GitHub answering us here"
    )


if __name__ == "__main__":
    raise SystemExit(main())
