"""ProbeLab's "Power By Agent Type" chart, landed as rows.

ProbeLab publishes Filecoin storage power split by the libp2p agent each miner's peer announces
(curio, boost, droplet, unknown, ...), but ONLY as JSON embedded in the HTML of an htmx chart
fragment. There is no JSON URL, and api.probelab.io needs an X-API-Key, so an http-json manifest
entry cannot read it. This model is the one exception to "no Python UDMs" -- see CLAUDE.md.

It is deliberately dumb: fetch the fragment, lift out the echarts `dataset.source` array, and
land every row exactly as published. No agent is singled out and nothing is summed or divided
here; the metric that reads this table does that in allowlisted `oso-sql`, so the number is
still defined in `registry/`, not in this file.

It fails loudly rather than landing a partial table: a non-200, a page with no `source` array,
an empty array, or rows missing the fields below all raise. A failed run leaves yesterday's
table in place, and the metric's staleness floor turns that into `indeterminate`.

The chart carries ONE snapshot (a single `timestamp`), refreshed by ProbeLab on its own
schedule; this is a FULL rebuild, so the table always holds the latest snapshot only. History
lives in data/observations.csv, not here.
"""

import json
from datetime import datetime, timezone

import oso
import pandas as pd

CHART_URL = "https://probelab.io/filecoin/mainnet/charts/miner-power/"
USER_AGENT = "filecoin-pgf-monitor (+https://github.com/filecoin-project/pgf-monitor)"
SOURCE_KEY = '"source":'
FIELDS = [
    "timestamp",
    "group_0",
    "quality_adj_power_gib",
    "raw_byte_power_gib",
    "unique_miners",
    "quality_adj_power_gib_total",
    "raw_byte_power_gib_total",
]


def parse_source(html: str) -> list[dict]:
    """The chart's `dataset.source` rows. Raises if the page no longer carries them."""
    at = html.find(SOURCE_KEY)
    if at < 0:
        raise RuntimeError("miner-power chart has no dataset.source array; page layout changed?")
    rows, _ = json.JSONDecoder().raw_decode(html, at + len(SOURCE_KEY))
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("miner-power dataset.source is empty")
    for row in rows:
        missing = [f for f in FIELDS if row.get(f) is None]
        if missing:
            raise RuntimeError(f"miner-power row missing {missing}: {row}")
    return rows


def to_frame(rows: list[dict], fetched_at: datetime) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            # echarts timestamps are epoch milliseconds, UTC
            "snapshot_at": pd.to_datetime([r["timestamp"] for r in rows], unit="ms"),
            "agent_group": [str(r["group_0"]) for r in rows],
            "quality_adj_power_gib": [float(r["quality_adj_power_gib"]) for r in rows],
            "raw_byte_power_gib": [float(r["raw_byte_power_gib"]) for r in rows],
            "unique_miners": [int(r["unique_miners"]) for r in rows],
            "quality_adj_power_gib_total": [float(r["quality_adj_power_gib_total"]) for r in rows],
            "raw_byte_power_gib_total": [float(r["raw_byte_power_gib_total"]) for r in rows],
            "fetched_at": pd.to_datetime([fetched_at.replace(tzinfo=None)] * len(rows)),
        }
    )
    # A UDM timestamp column must be datetime64[us]; pandas defaults to [ns].
    for col in ("snapshot_at", "fetched_at"):
        df[col] = df[col].astype("datetime64[us]")
    return df


@oso.model(
    external_origins=["https://probelab.io"],
    capabilities=oso.Capabilities(fetch=True),
    columns=[
        oso.Column(name="snapshot_at", type="timestamp"),
        oso.Column(name="agent_group", type="varchar"),
        oso.Column(name="quality_adj_power_gib", type="double"),
        oso.Column(name="raw_byte_power_gib", type="double"),
        oso.Column(name="unique_miners", type="bigint"),
        oso.Column(name="quality_adj_power_gib_total", type="double"),
        oso.Column(name="raw_byte_power_gib_total", type="double"),
        oso.Column(name="fetched_at", type="timestamp"),
    ],
)
def miner_power_by_agent(context: oso.Context) -> oso.DataFrame:
    fetched_at = datetime.now(timezone.utc)
    res = context.fetch(CHART_URL, headers={"User-Agent": USER_AGENT})
    if res.status != 200:
        raise RuntimeError(f"probelab miner-power returned HTTP {res.status}")
    return to_frame(parse_source(res.text()), fetched_at)
