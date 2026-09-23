"""The ProbeLab miner-power UDM, run offline against a captured chart fragment.

The UDM executes inside OSO's sandbox, where `oso` is the platform SDK; it is not installable
here, so a stub stands in for the decorator and the fetch. What is under test is the part that can
silently go wrong: lifting the echarts `dataset.source` array out of HTML and landing it unchanged.
Fixture captured 2026-09-23 from https://probelab.io/filecoin/mainnet/charts/miner-power/.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

UDM = Path("udms/probelab/miner_power_by_agent.py")
FIXTURE = Path("tests/fixtures/udms/probelab_miner_power.html")


class _Response:
    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self._body = body

    def text(self) -> str:
        return self._body


class _Context:
    def __init__(self, status: int, body: str) -> None:
        self._response = _Response(status, body)
        self.fetched: list[str] = []

    def fetch(self, url: str, headers: dict | None = None) -> _Response:
        self.fetched.append(url)
        return self._response


@pytest.fixture(scope="module")
def udm(tmp_path_factory):
    stub = types.ModuleType("oso")
    stub.model = lambda **_: (lambda fn: fn)
    stub.Capabilities = lambda **kw: kw
    stub.Column = lambda **kw: kw
    stub.Context = object
    stub.DataFrame = object
    sys.modules["oso"] = stub
    try:
        spec = importlib.util.spec_from_file_location("miner_power_by_agent", UDM)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        del sys.modules["oso"]
    return module


def test_lands_every_agent_row_unchanged(udm):
    ctx = _Context(200, FIXTURE.read_text())
    df = udm.miner_power_by_agent(ctx)

    assert ctx.fetched == [udm.CHART_URL]
    assert set(df["agent_group"]) == {
        "boost", "boost-curio", "booster-http", "curio", "droplet", "unknown",
    }
    curio = df[df["agent_group"] == "curio"].iloc[0]
    assert curio["unique_miners"] == 37
    assert curio["quality_adj_power_gib"] == 734164032.0
    assert str(curio["snapshot_at"]) == "2026-09-20 00:00:00"
    # every row carries the same network total, and the groups sum to it
    assert df["quality_adj_power_gib_total"].nunique() == 1
    assert df["quality_adj_power_gib"].sum() == df["quality_adj_power_gib_total"].iloc[0]


def test_timestamps_are_microsecond(udm):
    df = udm.miner_power_by_agent(_Context(200, FIXTURE.read_text()))
    assert str(df["snapshot_at"].dtype) == "datetime64[us]"
    assert str(df["fetched_at"].dtype) == "datetime64[us]"


@pytest.mark.parametrize(
    ("status", "body", "match"),
    [
        (503, "", "HTTP 503"),
        (200, "<div>no chart here</div>", "no dataset.source"),
        (200, '"source":[]', "empty"),
        (200, '"source":[{"timestamp":1,"group_0":"curio"}]', "missing"),
    ],
)
def test_fails_loudly_rather_than_landing_a_partial_table(udm, status, body, match):
    with pytest.raises(RuntimeError, match=match):
        udm.miner_power_by_agent(_Context(status, body))
