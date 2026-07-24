"""SLA observations: the append-only time series behind the dashboard's detail charts.

A single point-in-time verdict is useless for uptime-style SLAs. This script maintains
`data/observations.csv` (git-tracked, public facts) with one row per
(observed_at, team, function_id, metric):

- `backfill` — reconstructs history where the source's OWN data carries it (DefiLlama
  daily TVL, Blockscout daily indexing charts, GitHub release/commit event history,
  snapshot-archive listings, status-page incidents). Every backfilled row is labelled
  with its method; nothing is invented — days the source doesn't cover don't exist.
- `append --store DIR` — appends the live readings from a review run's ReviewBundles,
  so history accrues forward with every scheduled review.
- `upload --oso-org UUID` — pushes the CSV to the public `filpgf_sla_observations`
  static model.

Columns: observed_at, team, function_id, metric, observed_value, threshold_op,
threshold_value, sla_outcome, method, note. sla_outcome is computed against TODAY's
threshold (goalpost history is the registry's job, not this table's).

Usage:
  uv run python scripts/observations.py backfill [--days 365]
  uv run python scripts/observations.py append --store /tmp/fpm_all_store
  uv run python scripts/observations.py upload --oso-org <uuid>
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

CSV_PATH = Path("data/observations.csv")
COLUMNS = [
    "observed_at",
    "team",
    "function_id",
    "metric",
    "observed_value",
    "threshold_op",
    "threshold_value",
    "sla_outcome",
    "method",
    "note",
]
UA = {"User-Agent": "fpm-monitor/1.0 (+github.com/filecoin-project/pgf-monitor)"}


def _get(url: str, timeout: float = 30.0):
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _outcome(value: float | None, op: str, threshold: float) -> str:
    if value is None:
        return "indeterminate"
    ops = {
        ">=": value >= threshold,
        "<=": value <= threshold,
        ">": value > threshold,
        "<": value < threshold,
        "==": value == threshold,
    }
    return "pass" if ops[op] else "fail"


def _row(observed_at, team, fid, metric, value, op, threshold, method, note=""):
    return {
        "observed_at": observed_at.strftime("%Y-%m-%d") if hasattr(observed_at, "strftime") else observed_at,
        "team": team,
        "function_id": fid,
        "metric": metric,
        "observed_value": None if value is None else round(float(value), 6),
        "threshold_op": op,
        "threshold_value": threshold,
        "sla_outcome": _outcome(value, op, threshold) if op else "",
        "method": method,
        "note": note,
    }


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(str(s).replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# backfill strategies
# ---------------------------------------------------------------------------


def _daily_series_usdfc_tvl(cutoff: datetime) -> list[dict]:
    data = _get("https://api.llama.fi/protocol/usdfc")
    out = []
    for p in data.get("tvl", []):
        d = datetime.fromtimestamp(p["date"], tz=timezone.utc)
        if d >= cutoff:
            out.append(
                _row(d, "secured-finance", "usdfc-collateral-tvl-floor", "usdfc_tvl_usd",
                     p.get("totalLiquidityUSD"), ">=", 100_000,
                     "backfill:api.llama.fi", "daily protocol TVL history")
            )
    return out


def _daily_series_blockscout(cutoff: datetime) -> list[dict]:
    out = []
    for host, fid in (
        ("filecoin.blockscout.com", "fevm-mainnet-explorer-blockscout"),
        ("filecoin-testnet.blockscout.com", "calibnet-explorer-blockscout"),
    ):
        # the v2 chart caps at ~30 days; the stats-service line endpoint honors `from`
        data = _get(
            f"https://{host}/stats-service/api/v1/lines/newTxns"
            f"?resolution=DAY&from={cutoff.strftime('%Y-%m-%d')}"
        )
        for p in data.get("chart", []):
            d = _parse_dt(p["date"]).replace(tzinfo=timezone.utc)
            if d >= cutoff:
                out.append(
                    _row(d, "blockscout", fid, "daily_indexed_transactions",
                         float(p["value"]), ">", 0,
                         f"backfill:{host}",
                         "reconstructed operational history (explorer indexed the day); "
                         "live SLA metric is head-block age")
                )
    return out


_RELEASE_REPOS = [
    # (team, function_id, repo, metric, op, threshold, stable_filter)
    ("chainsafe", "forest-release-cadence", "ChainSafe/forest", "days_between_releases", "<=", 45, False),
    ("filoz", "curio-sealing-release-cadence", "filecoin-project/curio", "days_between_releases", "<=", 45, False),
    ("filoz", "lotus-consensus-client-release-cadence", "filecoin-project/lotus", "days_between_stable_releases", "<=", 60, True),
    ("filoz", "evm-eam-actor-maintenance", "filecoin-project/builtin-actors", "days_between_releases", "<=", 60, False),
    ("libp2p-networking", "libp2p-release-cadence", "libp2p/go-libp2p", "days_between_releases", "<=", 60, False),
]


def _release_series(cutoff: datetime) -> list[dict]:
    out = []
    for team, fid, repo, metric, op, thr, stable in _RELEASE_REPOS:
        rels = _get(f"https://api.github.com/repos/{repo}/releases?per_page=100")
        dates = sorted(
            _parse_dt(r["published_at"])
            for r in rels
            if r.get("published_at")
            and not (stable and ("rc" in (r.get("tag_name") or "").lower() or (r.get("tag_name") or "").startswith("miner/")))
        )
        for prev, cur in zip(dates, dates[1:]):
            if cur >= cutoff:
                gap = (cur - prev).total_seconds() / 86400.0
                out.append(_row(cur, team, fid, metric, gap, op, thr,
                                "backfill:api.github.com", f"gap since previous release of {repo}"))
    return out


_AGE_REPOS = [
    # weekly samples of days-since-latest-event as-of the sample date
    ("filoz", "builtin-actors", "filecoin-project/builtin-actors", "releases", "release_age_days", "<=", 90),
    ("proving", "rust-fil-proofs-maintenance", "filecoin-project/rust-fil-proofs", "commits", "proofs_days_since_last_commit", "<=", 120),
    ("proving", "proving-crypto-primitives-maintenance", "filecoin-project/bellperson", "commits", "bellperson_days_since_last_commit", "<=", 180),
    ("venus", "sophon-miner-maintenance", "ipfs-force-community/sophon-miner", "commits", "sophon_miner_days_since_last_commit", "<=", 120),
    ("venus", "damocles-maintenance", "ipfs-force-community/damocles", "commits", "damocles_days_since_last_commit", "<=", 120),
    ("lily", "lily-etl-maintenance", "filecoin-project/lily", "commits", "lily_days_since_last_commit", "<=", 90),
    ("fil-b", "network-documentation-commit-recency", "filecoin-project/filecoin-docs", "commits", "docs_last_commit_age_days", "<=", 60),
]


def _age_series(cutoff: datetime, now: datetime) -> list[dict]:
    out = []
    for team, fid, repo, kind, metric, op, thr in _AGE_REPOS:
        if kind == "releases":
            items = _get(f"https://api.github.com/repos/{repo}/releases?per_page=100")
            dates = sorted(_parse_dt(r["published_at"]) for r in items if r.get("published_at"))
        else:
            items = _get(f"https://api.github.com/repos/{repo}/commits?per_page=100")
            dates = sorted(_parse_dt(c["commit"]["committer"]["date"]) for c in items if c.get("commit"))
        if not dates:
            continue
        # weekly samples; only where the fetched event window can answer honestly
        # (a sample earlier than the oldest fetched event would overstate the age)
        sample = max(cutoff, dates[0])
        while sample <= now:
            past = [d for d in dates if d <= sample]
            if past:
                age = (sample - past[-1]).total_seconds() / 86400.0
                out.append(_row(sample, team, fid, metric, age, op, thr,
                                "backfill:api.github.com", f"weekly sample from {repo} {kind} history"))
            sample += timedelta(days=7)
    return out


def _snapshot_series(cutoff: datetime) -> list[dict]:
    out = []
    for net, fid, metric in (
        ("mainnet", "mainnet-snapshot-freshness", "snapshot_age_seconds"),
        ("calibnet", "calibnet-snapshot-freshness", "calibnet_snapshot_age_seconds"),
    ):
        data = _get(f"https://forest-archive.chainsafe.dev/list/{net}/latest-v2?format=json&limit=250")
        dates = sorted(_parse_dt(i["uploaded"]) for i in data.get("items", []))
        by_day: dict[str, float] = {}
        for prev, cur in zip(dates, dates[1:]):
            gap = (cur - prev).total_seconds()
            day = cur.strftime("%Y-%m-%d")
            by_day[day] = max(by_day.get(day, 0.0), gap)
        for day, gap in sorted(by_day.items()):
            if _parse_dt(day + "T00:00:00+00:00") >= cutoff:
                out.append(_row(day, "chainsafe", fid, metric + "_daily_max_gap", gap, "<=", 21600,
                                "backfill:forest-archive.chainsafe.dev",
                                f"max inter-snapshot gap that day ({net}, archive retention window)"))
    return out


def _status_series(cutoff: datetime) -> list[dict]:
    data = _get("https://status.filecoin.io/api/v2/incidents.json")
    by_month: dict[str, int] = {}
    for inc in data.get("incidents", []):
        d = _parse_dt(inc["created_at"])
        if d >= cutoff:
            by_month[d.strftime("%Y-%m-01")] = by_month.get(d.strftime("%Y-%m-01"), 0) + 1
    # months with zero incidents inside the window still count — fill them
    cur = cutoff.replace(day=1)
    now = datetime.now(timezone.utc)
    out = []
    while cur <= now:
        key = cur.strftime("%Y-%m-01")
        out.append(_row(key, "filecoin-infra-misc", "network-monitoring-status-page",
                        "incidents_in_month", by_month.get(key, 0), "", 0,
                        "backfill:status.filecoin.io", "incident history (informational, no SLA threshold)"))
        cur = (cur + timedelta(days=32)).replace(day=1)
    return out


# Teams that publish an Atlassian/statuspage.io page. Generalizable: add a row per team as
# more funded projects agree to surface a status page. Backfilled to per-day pass/fail bars.
STATUSPAGES = [
    ("randamu", "drand-relay-statuspage", "statuspage_impact_level",
     "https://drand.statuspage.io/api/v2/incidents.json"),
]


def _statuspage_daily_series(cutoff: datetime) -> list[dict]:
    """Per-day operator status from a team's own status page -> 0 (operational) / 1 (incident),
    so it renders as green/red uptime bars. Mainnet-scoped (testnet-only incidents skipped); an
    unresolved 'monitoring' notice marks only its created day, since components read operational."""
    now = datetime.now(timezone.utc)
    out = []
    for team, fid, metric, url in STATUSPAGES:
        data = _get(url)
        windows = []
        for inc in data.get("incidents", []):
            if "testnet" in (inc.get("name") or "").lower():
                continue
            start = _parse_dt(inc["created_at"]).date()
            end = _parse_dt(inc["resolved_at"]).date() if inc.get("resolved_at") else start
            windows.append((start, end))
        day = cutoff.date()
        while day <= now.date():
            down = 1 if any(s <= day <= e for s, e in windows) else 0
            out.append(_row(day.isoformat() + "T12:00:00+00:00", team, fid, metric,
                            down, "<=", 0, "backfill:" + url.split("/")[2],
                            "operator status page (self-reported): 1 = active incident that day"))
            day += timedelta(days=1)
    return out


def backfill(days: int) -> list[dict]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    rows: list[dict] = []
    for fn in (
        lambda: _daily_series_usdfc_tvl(cutoff),
        lambda: _daily_series_blockscout(cutoff),
        lambda: _release_series(cutoff),
        lambda: _age_series(cutoff, now),
        lambda: _snapshot_series(cutoff),
        lambda: _status_series(cutoff),
        lambda: _statuspage_daily_series(cutoff),
    ):
        try:
            got = fn()
            rows.extend(got)
            print(f"  {fn.__name__ if hasattr(fn, '__name__') else 'strategy'}: +{len(got)}")
        except Exception as exc:
            print(f"  strategy failed (skipped): {exc}", file=sys.stderr)
    return rows


# ---------------------------------------------------------------------------
# append (live readings) + IO + upload
# ---------------------------------------------------------------------------


def live_rows(store_dir: str) -> list[dict]:
    from fpm.store import JsonlRecordStore

    out = []
    for b in JsonlRecordStore(Path(store_dir)).all_bundles():
        r, sla, reading = b.recommendation, b.dossier.sla_result, b.dossier.reading
        out.append(
            _row(reading.claim.fetched_at, r.team, r.function_id, reading.metric,
                 sla.observed, sla.op, sla.threshold if sla.threshold is not None else 0,
                 "live-review", "scheduled review reading")
        )
    return out


def load_csv() -> list[dict]:
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open() as f:
        return list(csv.DictReader(f))


def save_csv(rows: list[dict]) -> None:
    seen = set()
    unique = []
    for r in rows:
        key = (r["observed_at"], r["team"], r["function_id"], r["metric"], r["method"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    unique.sort(key=lambda r: (r["team"], r["function_id"], str(r["observed_at"])))
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(unique)
    print(f"{CSV_PATH}: {len(unique)} rows")


def upload(org_id: str) -> None:
    import os

    from fpm.oso.static_model import GraphqlStaticModelClient

    client = GraphqlStaticModelClient(api_key=os.environ["OSO_API_KEY"], org_id=org_id)
    name = "filpgf_sla_observations"
    dataset_id = client.ensure_static_dataset(org_id, name)
    model_id = client.create_static_model(org_id, dataset_id, name)
    client.upload_csv(model_id, CSV_PATH.read_text())
    client.run_static_model(dataset_id)
    client.grant_public(model_id)
    print(f"uploaded {CSV_PATH} -> {name} (dataset {dataset_id})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="observations")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backfill")
    b.add_argument("--days", type=int, default=365)
    a = sub.add_parser("append")
    a.add_argument("--store", required=True)
    u = sub.add_parser("upload")
    u.add_argument("--oso-org", required=True)
    args = ap.parse_args(argv)

    if args.cmd == "backfill":
        save_csv(load_csv() + backfill(args.days))
    elif args.cmd == "append":
        save_csv(load_csv() + live_rows(args.store))
    elif args.cmd == "upload":
        upload(args.oso_org)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
