"""Liveness eval: probe every http-json source in the registry (adopted + drafts).

For each function entry, issue the declared request (GET, or POST with declared params)
and report reachability + whether the body parses as JSON. This is an on-demand eval
for reviewers ("are the metrics still probeable?"), not a CI gate — third-party
endpoints flake, and a flake is information, not a build failure.

Usage: uv run python scripts/probe_sources.py [--timeout 15] [--team TEAM]
Exit code: number of probe failures (0 = all reachable).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

from fpm.drafts import split_draft
from fpm.manifest import load_manifest


def iter_manifests(team: str | None):
    for path in sorted(Path("registry").glob("*.yaml")):
        if not path.name.startswith("_"):
            yield path, load_manifest(path), "adopted"
    for path in sorted(Path("registry/drafts").glob("*.yaml")):
        m, _ = split_draft(path)
        yield path, m, "draft"


# Some hosts (filfox /overview) 403 the default python-requests UA while accepting any
# other. Probe with an honest project UA; if an entry still fails, the OSO pipeline
# (dlt, requests-based UA) may hit the same wall — that's dry-run-gate material.
HEADERS = {"User-Agent": "fpm-monitor/1.0 (+github.com/filecoin-project/pgf-monitor)"}


def probe(fn, timeout: float) -> tuple[bool, str]:
    src = fn.source
    try:
        if src.method == "POST":
            r = requests.post(src.endpoint, json=src.params or {}, headers=HEADERS, timeout=timeout)
        else:
            r = requests.get(src.endpoint, params=src.params or None, headers=HEADERS, timeout=timeout)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        json.loads(r.text)
        return True, f"200 JSON ({len(r.text)}B)"
    except json.JSONDecodeError:
        return False, "200 but not JSON"
    except requests.RequestException as exc:
        return False, type(exc).__name__


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--team", default=None, help="only this team")
    args = ap.parse_args(argv)

    failures = 0
    for path, manifest, state in iter_manifests(args.team):
        if args.team and manifest.team != args.team:
            continue
        for fn in manifest.functions:
            if fn.source.kind != "http-json":
                print(f"SKIP {manifest.team}/{fn.function_id}: {fn.source.kind}")
                continue
            if fn.source.auth_secret_ref:
                print(f"SKIP {manifest.team}/{fn.function_id}: needs secret")
                continue
            ok, msg = probe(fn, args.timeout)
            print(f"{'OK  ' if ok else 'FAIL'} {manifest.team}/{fn.function_id} [{state}]: {msg}")
            failures += not ok
    print(f"\nfailures: {failures}")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
