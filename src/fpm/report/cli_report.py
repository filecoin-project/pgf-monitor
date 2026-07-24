"""Report CLI core, separated so tests can inject fetch without argparse or the network."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fpm.governance.allowlist import load_allowlist
from fpm.report.engine import run_report
from fpm.report.infer import FakeSourceInferrer, SourceInferrer
from fpm.report.probe import Fetch, _http_fetch


def run_report_cli(
    team: str,
    link: str,
    intent: str,
    function_id: str,
    as_of: datetime,
    out: str | None,
    live: bool,
    fetch: Fetch = _http_fetch,
    allowlist_path: str = "registry/_allowlist.txt",
) -> int:
    inferrer: SourceInferrer
    if live:
        from fpm.report.infer import SdkSourceInferrer

        inferrer = SdkSourceInferrer(model_id="claude-opus-4-8", prompt_version="0")
    else:
        inferrer = FakeSourceInferrer()
    d = run_report(
        intent, link, team, function_id, inferrer, load_allowlist(allowlist_path), as_of, fetch
    )
    endpoint = link
    print(f"From {endpoint} I read {d.metric} = {d.observed_value} (confidence {d.confidence})")
    for w in d.warnings:
        print(f"  WARNING: {w}")
    print("\n--- drafted manifest function (threshold intentionally omitted) ---")
    print(d.manifest_yaml)
    if out:
        Path(out).write_text(d.manifest_yaml)
        print(
            f"wrote {out}. Set the threshold, then merge into registry/{team}.yaml and open a PR."
        )
    else:
        print(f"Merge this into registry/{team}.yaml, set the threshold, then open a PR.")
    return 0
