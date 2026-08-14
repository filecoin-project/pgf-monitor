"""The nightly workflow is the only thing standing between this repo and a dead time series.

These assertions are deliberately about the properties that silently break a scheduled job:
it must actually be scheduled, it must be able to write back, and it must not quietly record a
night of indeterminate readings when its credentials are missing.
"""

from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/observe.yml")


def _workflow() -> dict:
    # PyYAML parses the unquoted key `on:` as the boolean True (the Norway problem's cousin).
    return yaml.safe_load(WORKFLOW.read_text())


def test_workflow_exists():
    assert WORKFLOW.is_file()


def test_it_is_actually_scheduled():
    triggers = _workflow()[True]
    assert "schedule" in triggers, "a nightly job that only runs on demand is not a nightly job"
    assert triggers["schedule"][0]["cron"]


def test_it_can_be_run_by_hand():
    assert "workflow_dispatch" in _workflow()[True]


def test_it_may_commit_the_readings():
    assert _workflow()["permissions"]["contents"] == "write"


def test_it_runs_the_readings_only_path():
    # Comments may mention `fpm review` (they explain why it is NOT here); commands may not.
    commands = "\n".join(
        line for line in WORKFLOW.read_text().splitlines() if not line.lstrip().startswith("#")
    )
    assert "fpm observe" in commands
    assert "fpm review" not in commands, "adjudication is a human act; it must not run unattended"
    assert "--dev-auto-approve" not in commands


def test_it_fetches_for_real():
    assert "--live-oso" in WORKFLOW.read_text()


def test_missing_credentials_fail_the_run():
    body = WORKFLOW.read_text()
    assert "OSO_API_KEY secret is not set" in body
