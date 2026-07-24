"""Quarantined live report smoke: real SdkSourceInferrer + real HTTP probe. Prints a draft, writes nothing.

Usage: uv run python scripts/live_report_smoke.py
"""

from __future__ import annotations

from datetime import datetime, timezone

from fpm.report.cli_report import run_report_cli


def main() -> None:
    run_report_cli(
        team="chainsafe",
        link="https://api.llama.fi/v2/historicalChainTvl/Filecoin",
        intent="Filecoin chain TVL should stay healthy, measured monthly",
        function_id="filecoin-tvl",
        as_of=datetime(2026, 7, 1, tzinfo=timezone.utc),
        out=None,
        live=True,
    )


if __name__ == "__main__":
    main()
