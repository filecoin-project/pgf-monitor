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
- `upload --oso-org UUID` — pushes `data/observations.csv` to the public
  `filpgf_sla_observations` static model.
- `upload-thresholds --oso-org UUID` — pushes `data/thresholds.csv` (see
  `fpm.thresholds`) to the public `filpgf_sla_thresholds` static model.

Columns: observed_at, team, function_id, metric, observed_value, method, note. Measurement
only — the bar a value is judged against lives in `data/thresholds.csv` (see
`fpm.thresholds`), published as `filpgf_sla_thresholds`.

Usage:
  uv run python scripts/observations.py backfill [--days 365]
  uv run python scripts/observations.py append --store /tmp/fpm_all_store
  uv run python scripts/observations.py upload --oso-org <uuid>
  uv run python scripts/observations.py upload-thresholds --oso-org <uuid>
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from fpm import observations as fpm_observations

CSV_PATH = Path("data/observations.csv")
COLUMNS = fpm_observations.COLUMNS
UA = {"User-Agent": "fpm-monitor/1.0 (+github.com/filecoin-project/pgf-monitor)"}


def _get(url: str, timeout: float = 30.0):
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _row(observed_at, team, fid, metric, value, method, note=""):
    return {
        "observed_at": observed_at.strftime("%Y-%m-%d")
        if hasattr(observed_at, "strftime")
        else observed_at,
        "team": team,
        "function_id": fid,
        "metric": metric,
        "observed_value": None if value is None else round(float(value), 6),
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
                _row(
                    d,
                    "secured-finance",
                    "usdfc-collateral-tvl-floor",
                    "usdfc_tvl_usd",
                    p.get("totalLiquidityUSD"),
                    "backfill:api.llama.fi",
                    "daily protocol TVL history",
                )
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
                    _row(
                        d,
                        "blockscout",
                        fid,
                        "daily_indexed_transactions",
                        float(p["value"]),
                        f"backfill:{host}",
                        "reconstructed operational history (explorer indexed the day); "
                        "live SLA metric is head-block age",
                    )
                )
    return out


_RELEASE_REPOS = [
    # (team, function_id, repo, metric, op, threshold, stable_filter)
    (
        "chainsafe",
        "forest-release-cadence",
        "ChainSafe/forest",
        "days_between_releases",
        "<=",
        45,
        False,
    ),
    (
        "filoz",
        "curio-sealing-release-cadence",
        "filecoin-project/curio",
        "days_between_releases",
        "<=",
        45,
        False,
    ),
    (
        "filoz",
        "lotus-consensus-client-release-cadence",
        "filecoin-project/lotus",
        "days_between_stable_releases",
        "<=",
        60,
        True,
    ),
    (
        "filoz",
        "evm-eam-actor-maintenance",
        "filecoin-project/builtin-actors",
        "days_between_releases",
        "<=",
        60,
        False,
    ),
    (
        "libp2p-networking",
        "libp2p-release-cadence",
        "libp2p/go-libp2p",
        "days_between_releases",
        "<=",
        60,
        False,
    ),
]


def _release_series(cutoff: datetime) -> list[dict]:
    out = []
    for team, fid, repo, metric, _op, _thr, stable in _RELEASE_REPOS:
        rels = _get(f"https://api.github.com/repos/{repo}/releases?per_page=100")
        dates = sorted(
            _parse_dt(r["published_at"])
            for r in rels
            if r.get("published_at")
            and not (
                stable
                and (
                    "rc" in (r.get("tag_name") or "").lower()
                    or (r.get("tag_name") or "").startswith("miner/")
                )
            )
        )
        for prev, cur in zip(dates, dates[1:]):
            if cur >= cutoff:
                gap = (cur - prev).total_seconds() / 86400.0
                out.append(
                    _row(
                        cur,
                        team,
                        fid,
                        metric,
                        gap,
                        "backfill:api.github.com",
                        f"gap since previous release of {repo}",
                    )
                )
    return out


_AGE_REPOS = [
    # weekly samples of days-since-latest-event as-of the sample date
    (
        "filoz",
        "builtin-actors",
        "filecoin-project/builtin-actors",
        "releases",
        "release_age_days",
        "<=",
        90,
    ),
    (
        "proving",
        "rust-fil-proofs-maintenance",
        "filecoin-project/rust-fil-proofs",
        "commits",
        "proofs_days_since_last_commit",
        "<=",
        120,
    ),
    (
        "proving",
        "proving-crypto-primitives-maintenance",
        "filecoin-project/bellperson",
        "commits",
        "bellperson_days_since_last_commit",
        "<=",
        180,
    ),
    (
        "venus",
        "sophon-miner-maintenance",
        "ipfs-force-community/sophon-miner",
        "commits",
        "sophon_miner_days_since_last_commit",
        "<=",
        120,
    ),
    (
        "venus",
        "damocles-maintenance",
        "ipfs-force-community/damocles",
        "commits",
        "damocles_days_since_last_commit",
        "<=",
        120,
    ),
    (
        "lily",
        "lily-etl-maintenance",
        "filecoin-project/lily",
        "commits",
        "lily_days_since_last_commit",
        "<=",
        90,
    ),
    (
        "fil-b",
        "network-documentation-commit-recency",
        "filecoin-project/filecoin-docs",
        "commits",
        "docs_last_commit_age_days",
        "<=",
        60,
    ),
]


def _age_series(cutoff: datetime, now: datetime) -> list[dict]:
    out = []
    for team, fid, repo, kind, metric, _op, _thr in _AGE_REPOS:
        if kind == "releases":
            items = _get(f"https://api.github.com/repos/{repo}/releases?per_page=100")
            dates = sorted(_parse_dt(r["published_at"]) for r in items if r.get("published_at"))
        else:
            items = _get(f"https://api.github.com/repos/{repo}/commits?per_page=100")
            dates = sorted(
                _parse_dt(c["commit"]["committer"]["date"]) for c in items if c.get("commit")
            )
        if not dates:
            continue
        # weekly samples; only where the fetched event window can answer honestly
        # (a sample earlier than the oldest fetched event would overstate the age)
        sample = max(cutoff, dates[0])
        while sample <= now:
            past = [d for d in dates if d <= sample]
            if past:
                age = (sample - past[-1]).total_seconds() / 86400.0
                out.append(
                    _row(
                        sample,
                        team,
                        fid,
                        metric,
                        age,
                        "backfill:api.github.com",
                        f"weekly sample from {repo} {kind} history",
                    )
                )
            sample += timedelta(days=7)
    return out


def _snapshot_series(cutoff: datetime) -> list[dict]:
    out = []
    for net, fid, metric in (
        ("mainnet", "mainnet-snapshot-freshness", "snapshot_age_seconds"),
        ("calibnet", "calibnet-snapshot-freshness", "calibnet_snapshot_age_seconds"),
    ):
        data = _get(
            f"https://forest-archive.chainsafe.dev/list/{net}/latest-v2?format=json&limit=250"
        )
        dates = sorted(_parse_dt(i["uploaded"]) for i in data.get("items", []))
        by_day: dict[str, float] = {}
        for prev, cur in zip(dates, dates[1:]):
            gap = (cur - prev).total_seconds()
            day = cur.strftime("%Y-%m-%d")
            by_day[day] = max(by_day.get(day, 0.0), gap)
        for day, gap in sorted(by_day.items()):
            if _parse_dt(day + "T00:00:00+00:00") >= cutoff:
                out.append(
                    _row(
                        day,
                        "chainsafe",
                        fid,
                        metric + "_daily_max_gap",
                        gap,
                        "backfill:forest-archive.chainsafe.dev",
                        f"max inter-snapshot gap that day ({net}, archive retention window)",
                    )
                )
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
        out.append(
            _row(
                key,
                "filecoin-infra-misc",
                "network-monitoring-status-page",
                "incidents_in_month",
                by_month.get(key, 0),
                "backfill:status.filecoin.io",
                "incident history (informational, no SLA threshold)",
            )
        )
        cur = (cur + timedelta(days=32)).replace(day=1)
    return out


# Teams that publish an Atlassian/statuspage.io page. Generalizable: add a row per team as
# more funded projects agree to surface a status page. Backfilled to per-day pass/fail bars.
STATUSPAGES = [
    (
        "randamu",
        "drand-relay-statuspage",
        "statuspage_impact_level",
        "https://drand.statuspage.io/api/v2/incidents.json",
    ),
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
            out.append(
                _row(
                    day.isoformat() + "T12:00:00+00:00",
                    team,
                    fid,
                    metric,
                    down,
                    "backfill:" + url.split("/")[2],
                    "operator status page (self-reported): 1 = active incident that day",
                )
            )
            day += timedelta(days=1)
    return out


# ---------------------------------------------------------------------------
# Recovered after the 2026-08-22/23 platform outage. Both sources keep their own history, so
# these two metric-days are real readings rather than imputations -- which is why they belong
# here, in the system of record, and not in the mart's presentation layer.
#
# READ ANCHOR: 05:30 UTC, the hour the nightly actually reads (cron 05:23, run starts ~05:28).
# Not cosmetic -- both metrics are time-of-day dependent, and the anchor is what makes a
# reconstruction comparable to a nightly reading. Validated against two days the nightly DID
# record: see tests/test_observations_backfill.py.
# ---------------------------------------------------------------------------

# The anchor is ERA-AWARE, and it has to be. observe.yml's cron moved from 06:17 to 05:23 UTC on
# 2026-08-25, so a single anchor is wrong on one side of that date or the other. Measured, not
# assumed: implied read time = (newest run before a nightly reading) + that reading's age, over
# every nightly row of pipeline_success_age_days.
#
#   2026-08-16 .. 2026-08-25   06:32, 06:38, 06:38, 06:33, 06:39, 06:34, 06:39   -> 06:36
#   2026-08-26 onward          05:42, 06:03, 05:43                               -> 05:50
#
# The boundary is 08-26, NOT 08-25: the cron change (8df156b) landed 2026-08-25 06:59 UTC, AFTER
# that morning's 06:17 run, so 08-25 itself is still old-era. Getting this off by one day left
# 08-25 reconstructed 46.6 minutes early -- 0.636701 against the nightly's 0.669067.
#
# (Dates whose run was re-triggered by hand -- 08-24 at 15:33, 08-27/28 at ~17:00 -- are excluded
# as contaminated.) Getting this wrong is not cosmetic: a 05:30 anchor reconstructed the outage
# days 66 minutes early and disagreed with every neighbouring nightly reading by ~7%.
READ_ANCHORS = (
    ("2026-08-26", (6, 36)),  # days BEFORE this date: the 06:17 cron era
    (None, (5, 50)),  # from that date on: the 05:23 cron era
)


def _anchor(day: datetime) -> datetime:
    """The instant a nightly reading for `day` would have been taken."""
    iso = day.strftime("%Y-%m-%d")
    for boundary, (hh, mm) in READ_ANCHORS:
        if boundary is None or iso < boundary:
            return day.replace(hour=hh, minute=mm, second=0, microsecond=0)
    raise AssertionError("unreachable: READ_ANCHORS must end with a None boundary")


def age_days_at(event_times: list[datetime], sample: datetime) -> float | None:
    """Age in days of the newest event at or before `sample`. None when nothing precedes it."""
    past = [t for t in event_times if t <= sample]
    if not past:
        return None
    return (sample - max(past)).total_seconds() / 86400.0


def trailing_window_sum(buckets: list[tuple[datetime, float]], sample: datetime, hours: int = 24):
    """Sum bucket values in [sample - hours, sample).

    This is what `volume_usd.h24` means: a TRAILING window at read time, not a calendar day.
    Summing calendar days instead is off by a factor that varies with read hour -- 08-21 reads
    59,962 as h24 against 29,072 for the calendar day.
    """
    start = sample - timedelta(hours=hours)
    inside = [v for t, v in buckets if start <= t < sample]
    if not inside:
        return None
    return sum(inside)


def _pipeline_success_series(cutoff: datetime) -> list[dict]:
    """filecoin-data-portal pipeline freshness, from GitHub Actions run history.

    A successful run exists on every day of the outage, so the age is exact, not estimated.
    """
    runs = _get(
        "https://api.github.com/repos/davidgasquez/filecoin-data-portal/actions/workflows/"
        "pipeline.yml/runs?status=success&per_page=100"
    )
    dates = sorted(_parse_dt(r["created_at"]) for r in runs.get("workflow_runs", []))
    if not dates:
        return []
    out = []
    day = max(cutoff, dates[0]).replace(hour=0, minute=0, second=0, microsecond=0)
    now = datetime.now(timezone.utc)
    while day <= now:
        sample = _anchor(day)
        if sample > now:
            break  # today's anchor has not arrived yet; a row here would be read from the future
        age = age_days_at(dates, sample)
        if age is not None and sample >= dates[0]:
            out.append(
                _row(
                    sample,
                    "filecoin-data-portal",
                    "network-data-portal-pipeline-freshness",
                    "pipeline_success_age_days",
                    age,
                    "backfill:api.github.com",
                    "daily sample from pipeline.yml successful-run history",
                )
            )
        day += timedelta(days=1)
    return out


def _pool_volume_series(cutoff: datetime) -> list[dict]:
    """USDFC pool 24h volume, rebuilt from GeckoTerminal HOURLY candles.

    Hourly, not daily, because the metric is a trailing 24h window (see trailing_window_sum).
    """
    pool = "0x21ca72fe39095db9642ca9cc694fa056f906037f"
    data = _get(
        f"https://api.geckoterminal.com/api/v2/networks/filecoin/pools/{pool}/ohlcv/hour?limit=1000"
    )
    lst = (((data.get("data") or {}).get("attributes") or {}).get("ohlcv_list")) or []
    buckets = sorted((datetime.fromtimestamp(int(r[0]), timezone.utc), float(r[5])) for r in lst)
    if not buckets:
        return []
    out = []
    day = max(cutoff, buckets[0][0]).replace(hour=0, minute=0, second=0, microsecond=0)
    now = datetime.now(timezone.utc)
    while day <= now:
        sample = _anchor(day)
        if sample > now:
            break  # a trailing window ending in the future silently undercounts the tail hours
        total = trailing_window_sum(buckets, sample)
        if total is not None and sample - timedelta(hours=24) >= buckets[0][0]:
            out.append(
                _row(
                    sample,
                    "secured-finance",
                    "usdfc-axlusdc-pool-volume",
                    "usdfc_pool_volume_usd",
                    total,
                    "backfill:api.geckoterminal.com",
                    "trailing-24h volume rebuilt from hourly candles at the nightly read hour",
                )
            )
        day += timedelta(days=1)
    return out


# TARGETED_ONLY strategies are reachable via `--only` and are NOT in the default rotation.
# Both were written to recover the 2026-08-22/23 outage, and both emit a row per day for as far
# back as their source reaches -- 115 days for the GitHub run history, 53 for GeckoTerminal's
# hourly candles. About half of that is genuinely new history and worth having; the other half
# lands a second row beside an existing nightly reading for the same metric-day, which the mart
# renders as a second series. That is documented behaviour, not a bug, but it should be a
# deliberate act rather than a side effect of running `backfill` with its default --days 365.
TARGETED_ONLY = frozenset({"pipeline-success", "pool-volume"})


def select_strategies(available: list[str], only: list[str] | None) -> list[str]:
    """Which backfill strategies to run. Raises on an unknown name rather than silently skipping."""
    if only:
        unknown = sorted(set(only) - set(available))
        if unknown:
            raise SystemExit(
                f"unknown strategy: {', '.join(unknown)}; choose from {', '.join(available)}"
            )
        return [s for s in available if s in only]
    return [s for s in available if s not in TARGETED_ONLY]


def backfill(
    days: int, only: list[str] | None = None, dates: list[str] | None = None
) -> list[dict]:
    """Rebuild history from sources that keep their own.

    `only` names strategies to run; `dates` restricts which observation days are emitted.
    Without `only`, every strategy EXCEPT TARGETED_ONLY runs. Naming the strategies (rather
    than a bare tuple of lambdas) is what makes both filters possible, and it also puts a
    source name in the progress output.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    strategies = {
        "usdfc-tvl": lambda: _daily_series_usdfc_tvl(cutoff),
        "blockscout": lambda: _daily_series_blockscout(cutoff),
        "releases": lambda: _release_series(cutoff),
        "ages": lambda: _age_series(cutoff, now),
        "snapshots": lambda: _snapshot_series(cutoff),
        "status": lambda: _status_series(cutoff),
        "statuspage": lambda: _statuspage_daily_series(cutoff),
        "pipeline-success": lambda: _pipeline_success_series(cutoff),
        "pool-volume": lambda: _pool_volume_series(cutoff),
    }
    stale = TARGETED_ONLY - set(strategies)
    if stale:
        raise AssertionError(
            f"TARGETED_ONLY names no such strategy: {', '.join(sorted(stale))}. Left unchecked, a "
            f"rename silently re-admits it to the default rotation."
        )
    chosen = select_strategies(sorted(strategies), only)
    strategies = {k: v for k, v in strategies.items() if k in chosen}
    wanted = set(dates or ())
    rows: list[dict] = []
    for name, fn in strategies.items():
        try:
            got = fn()
            if wanted:
                got = [r for r in got if r["observed_at"] in wanted]
            rows.extend(got)
            print(f"  {name}: +{len(got)}")
        except Exception as exc:
            print(f"  {name} failed (skipped): {exc}", file=sys.stderr)
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
            _row(
                reading.claim.fetched_at,
                r.team,
                r.function_id,
                reading.metric,
                sla.observed,
                "live-review",
                "scheduled review reading",
            )
        )
    return out


def void_readings(voids: list[dict], path=None) -> int:
    """Replace a published reading with a null and a reason, through the normal merge path.

    For a reading that is WRONG rather than missing. A null is honest -- it says the day has no
    defensible number, which is exactly true of a reading we can prove false. Inventing a
    replacement would be worse, and deleting the row would erase the fact that the nightly ran.

    `merge` is last-wins on (team, function_id, metric, observed_at, method), so a void carries
    the SAME method as the row it replaces; that is what makes it land on the original rather
    than beside it. Any real value recovered separately keeps its own `backfill:<host>` method
    and is untouched.
    """
    from fpm import observations as obs

    target = path or obs.CSV_PATH
    rows = obs.load_rows(target)
    keys = {obs.row_key(r) for r in rows}
    new = []
    for v in voids:
        row = {
            "observed_at": v["date"],
            "team": v["team"],
            "function_id": v["function_id"],
            "metric": v["metric"],
            "observed_value": None,
            "method": v.get("method", "nightly"),
            "note": v["note"],
        }
        if obs.row_key(row) not in keys:
            raise SystemExit(
                f"nothing to void: no {v['method']} reading for {v['team']}/{v['metric']} on "
                f"{v['date']}. Voiding a row that does not exist would ADD a null rather than "
                f"replace a value."
            )
        new.append(row)
    obs.save_rows(obs.merge(rows, new), target)
    return len(new)


def load_csv() -> list[dict]:
    return fpm_observations.load_rows(CSV_PATH)


def save_csv(rows: list[dict]) -> None:
    """Delegates to fpm.observations so this script and `fpm observe` write one identical table.

    That module normalizes `observed_at` to a UTC date before deduping — without it the same
    metric-day lands twice as `2026-07-19` and `2026-07-19T12:00:00+00:00`, which is what the
    shipped CSV used to carry.
    """
    merged = fpm_observations.merge([], rows)
    fpm_observations.save_rows(merged, CSV_PATH)
    print(f"{CSV_PATH}: {len(merged)} rows")


def upload(org_id: str, csv_path: Path, name: str) -> None:
    import os

    from fpm.oso.static_model import GraphqlStaticModelClient

    client = GraphqlStaticModelClient(api_key=os.environ["OSO_API_KEY"], org_id=org_id)
    dataset_id = client.ensure_static_dataset(org_id, name)
    # ensure_, not create_: this republishes the SAME table every run, so creating
    # unconditionally fails with ALREADY_EXISTS from the second upload onward.
    model_id = client.ensure_static_model(org_id, dataset_id, name)
    client.upload_csv(model_id, csv_path.read_text())
    client.run_static_model(dataset_id, model_id)
    client.grant_public(model_id)
    print(f"uploaded {csv_path} -> {name} (dataset {dataset_id})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="observations")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backfill")
    b.add_argument("--days", type=int, default=365)
    b.add_argument(
        "--only", action="append", default=None, help="run only this strategy (repeatable)"
    )
    b.add_argument(
        "--date",
        action="append",
        default=None,
        dest="dates",
        help="emit only this observation day, YYYY-MM-DD (repeatable). A backfill row "
        "earns its place when it supplies something the nightly did not -- a "
        "missing value or a demonstrably wrong one -- not when it merely agrees.",
    )
    a = sub.add_parser("append")
    a.add_argument("--store", required=True)
    vd = sub.add_parser("void", help="null a reading that is wrong rather than missing")
    vd.add_argument("--date", required=True)
    vd.add_argument("--team", required=True)
    vd.add_argument("--function-id", required=True)
    vd.add_argument("--metric", required=True)
    vd.add_argument("--method", default="nightly")
    vd.add_argument("--note", required=True, help="why this reading cannot be trusted")
    u = sub.add_parser("upload")
    u.add_argument("--oso-org", required=True)
    ut = sub.add_parser("upload-thresholds")
    ut.add_argument("--oso-org", required=True)
    args = ap.parse_args(argv)

    if args.cmd == "backfill":
        save_csv(load_csv() + backfill(args.days, args.only, args.dates))
    elif args.cmd == "append":
        save_csv(load_csv() + live_rows(args.store))
    elif args.cmd == "void":
        n = void_readings(
            [
                {
                    "date": args.date,
                    "team": args.team,
                    "function_id": args.function_id,
                    "metric": args.metric,
                    "method": args.method,
                    "note": args.note,
                }
            ]
        )
        print(f"voided {n} reading(s)")
    elif args.cmd == "upload":
        upload(args.oso_org, CSV_PATH, "filpgf_sla_observations")
    elif args.cmd == "upload-thresholds":
        from fpm.thresholds import CSV_PATH as THRESHOLDS_CSV

        upload(args.oso_org, THRESHOLDS_CSV, "filpgf_sla_thresholds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
