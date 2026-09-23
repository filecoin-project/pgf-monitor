"""Deploy the repo's Python UDMs to OSO, so what runs on the platform is what is in git.

  uv run python scripts/deploy_udms.py --oso-org UUID [--run] [--dry-run]

Every `udms/<dataset>/<model>.py` becomes model `<model>` in USER_MODEL dataset `<dataset>` of the
org. The dataset is created if missing, given the cron in DATASET_CRONS, and made public-read (the
upstream is a public page, so the landed table should be as readable as the page is). A new
revision + release is pushed ONLY when the code differs from the model's latest revision, so a
no-op deploy leaves the platform untouched.

This is the deploy half of the one exception to "no Python UDMs" (see CLAUDE.md): the code lives
here, under CODEOWNERS, and `.github/workflows/deploy-udms.yml` runs this on merge to main. Do not
edit these models on the platform directly -- the next deploy will overwrite the edit.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

import requests

API = "https://api.oso.xyz/v1/graphql"
UDM_ROOT = Path("udms")

# Before observe.yml (05:23 UTC) so the nightly reads today's landing, and off the hour.
DATASET_CRONS = {"probelab": "41 3 * * *"}

_COLUMN = re.compile(r'oso\.Column\(name="([^"]+)",\s*type="([^"]+)"\)')
_TERMINAL = {"SUCCESS", "FAILED", "CANCELED"}


def _gql(query: str, variables: dict) -> dict:
    r = requests.post(
        API,
        json={"query": query, "variables": variables},
        headers={
            "Authorization": f"Bearer {os.environ['OSO_API_KEY']}",
            # api.oso.xyz 403s python's default user agents
            "User-Agent": "curl/8.5.0",
        },
        timeout=60,
    )
    r.raise_for_status()
    body = r.json()
    if body.get("errors"):
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    return body["data"]


def discover(root: Path = UDM_ROOT) -> list[tuple[str, str, Path]]:
    """(dataset, model, path) for every UDM file, sorted for a stable deploy order."""
    return sorted((p.parent.name, p.stem, p) for p in root.glob("*/*.py"))


def schema_of(code: str) -> list[dict]:
    cols = [{"name": n, "type": t} for n, t in _COLUMN.findall(code)]
    if not cols:
        raise SystemExit("no oso.Column(...) declarations found; the revision needs a schema")
    return cols


def ensure_dataset(org_id: str, name: str, dry_run: bool) -> str | None:
    d = _gql(
        "query($w:JSON){ datasets(first:10, where:$w){ edges{ node{ id name orgId cron isPublic } } } }",
        {"w": {"name": {"eq": name}, "org_id": {"eq": org_id}}},
    )
    nodes = [e["node"] for e in d["datasets"]["edges"] if e["node"]["orgId"] == org_id]
    if nodes:
        ds = nodes[0]
    elif dry_run:
        print(f"[dry-run] would create USER_MODEL dataset {name}")
        return None
    else:
        ds = _gql(
            "mutation($i:CreateDatasetInput!){ createDataset(input:$i){ dataset{ id cron isPublic } } }",
            {
                "i": {
                    "orgId": org_id,
                    "name": name,
                    "displayName": name,
                    "type": "USER_MODEL",
                    "description": "Python UDMs deployed from filecoin-project/pgf-monitor udms/",
                }
            },
        )["createDataset"]["dataset"]
        print(f"created dataset {name} {ds['id']}")
    cron = DATASET_CRONS.get(name)
    if cron and ds.get("cron") != cron and not dry_run:
        _gql(
            "mutation($i:UpdateDatasetInput!){ updateDataset(input:$i){ success } }",
            {"i": {"id": ds["id"], "cron": cron, "cronTimezone": "UTC"}},
        )
        print(f"dataset {name}: cron -> {cron}")
    if not ds.get("isPublic") and not dry_run:
        _gql(
            "mutation($i:GrantResourcePermissionInput!){ grantResourcePermission(input:$i){ success } }",
            {"i": {"id": ds["id"], "resourceType": "DATASET", "permissionLevel": "READ"}},
        )
        print(f"dataset {name}: granted public READ")
    return ds["id"]


def ensure_model(org_id: str, dataset_id: str, name: str) -> dict:
    d = _gql(
        "query($w:JSON){ dataModels(first:10, where:$w){ edges{ node{ id name dataset{ id } "
        "latestRelease{ revision{ id code } } } } } }",
        {"w": {"name": {"eq": name}, "dataset_id": {"eq": dataset_id}}},
    )
    for e in d["dataModels"]["edges"]:
        if e["node"]["dataset"]["id"] == dataset_id:
            return e["node"]
    m = _gql(
        "mutation($i:CreateDataModelInput!){ createDataModel(input:$i){ dataModel{ id } } }",
        {"i": {"orgId": org_id, "datasetId": dataset_id, "name": name, "isEnabled": True}},
    )["createDataModel"]["dataModel"]
    print(f"created model {name} {m['id']}")
    return {"id": m["id"], "latestRelease": None}


def release(model: dict, name: str, code: str) -> bool:
    """Push a revision + release if the code changed. True when something was released."""
    # Compare against what is RELEASED, not the latest revision: a revision whose release failed
    # would otherwise read as "unchanged" on every later deploy and the platform would keep
    # running the old code with a green workflow.
    released = ((model.get("latestRelease") or {}).get("revision") or {}).get("code")
    if released == code:
        print(f"{name}: unchanged, nothing to release")
        return False
    desc = (code.split('"""')[1].strip().splitlines() or [name])[0] if '"""' in code else name
    rev = _gql(
        "mutation($i:CreateDataModelRevisionInput!){ createDataModelRevision(input:$i){ "
        "success message dataModelRevision{ id revisionNumber } } }",
        {
            "i": {
                "dataModelId": model["id"],
                "name": name,
                "language": "python",
                "code": code,
                "schema": schema_of(code),
                "kind": "FULL",
                "description": desc,
            }
        },
    )["createDataModelRevision"]
    if not rev["success"]:
        raise SystemExit(f"{name}: revision rejected: {rev['message']}")
    rel = _gql(
        "mutation($i:CreateDataModelReleaseInput!){ createDataModelRelease(input:$i){ success message } }",
        {
            "i": {
                "dataModelId": model["id"],
                "dataModelRevisionId": rev["dataModelRevision"]["id"],
                "description": desc,
            }
        },
    )["createDataModelRelease"]
    if not rel["success"]:
        raise SystemExit(f"{name}: release rejected: {rel['message']}")
    print(f"{name}: released revision {rev['dataModelRevision']['revisionNumber']}")
    return True


def run_and_wait(dataset_id: str, model_id: str, name: str, attempts: int = 60) -> None:
    d = _gql(
        "mutation($i:CreateUserModelRunRequestInput!){ createUserModelRunRequest(input:$i){ "
        "success message runGroup{ id runs{ edges{ node{ id } } } } } }",
        {"i": {"datasetId": dataset_id, "selectedModels": [model_id]}},
    )["createUserModelRunRequest"]
    # Run requests return a run GROUP since OSO's 2026-08 migration; the run is inside it.
    edges = (((d.get("runGroup") or {}).get("runs") or {}).get("edges")) or []
    if not d["success"] or not edges:
        raise SystemExit(f"{name}: run request returned no run: {d.get('message')!r}")
    run_id = edges[0]["node"]["id"]
    for _ in range(attempts):
        time.sleep(10)
        run = _gql(
            "query($w:JSON){ runs(first:1, where:$w){ edges{ node{ id status logsUrl } } } }",
            {"w": {"id": {"eq": run_id}}},
        )["runs"]["edges"]
        status = run[0]["node"]["status"] if run else None
        if status in _TERMINAL:
            print(f"{name}: run {run_id} {status}")
            if status != "SUCCESS":
                raise SystemExit(f"{name}: run {status}; logs {run[0]['node'].get('logsUrl')}")
            return
    raise SystemExit(f"{name}: run {run_id} not terminal after {attempts * 10}s")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="deploy_udms")
    ap.add_argument("--oso-org", required=True)
    ap.add_argument("--run", action="store_true", help="run each released model and wait for it")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if not os.environ.get("OSO_API_KEY"):
        print("OSO_API_KEY is not set", file=sys.stderr)
        return 1
    for dataset, name, path in discover():
        code = path.read_text()
        schema_of(code)  # fail before touching the platform
        dataset_id = ensure_dataset(args.oso_org, dataset, args.dry_run)
        if args.dry_run:
            print(f"[dry-run] {dataset}.{name}: {len(schema_of(code))} columns")
            continue
        model = ensure_model(args.oso_org, dataset_id, name)
        changed = release(model, name, code)
        if args.run and changed:
            run_and_wait(dataset_id, model["id"], name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
