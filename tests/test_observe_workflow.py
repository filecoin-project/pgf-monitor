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
    assert "OSO_ORG_ID variable is not set" in body


def test_credentials_come_from_the_right_place():
    """In this repo OSO_API_KEY is a secret and OSO_ORG_ID is a repository VARIABLE.

    Reading a variable through `secrets.` yields an empty string with no error, so the job would
    fail its own credential check every night for a reason the logs make look like a missing
    secret. Assert each is read from the context that actually holds it.
    """
    body = WORKFLOW.read_text()
    assert "secrets.OSO_API_KEY" in body
    assert "vars.OSO_ORG_ID" in body
    assert "secrets.OSO_ORG_ID" not in body


def test_a_night_that_collected_nothing_fails_the_workflow():
    """The gap this closes: `fpm observe` isolates per-function fetch failures, so a failure that
    hits EVERY function exits 0. Between 2026-08-22 and 2026-08-24 the workflow reported success
    three times while every reading landed value-less."""
    body = WORKFLOW.read_text()
    assert "scripts.check_collection" in body


def test_the_blackout_check_runs_after_the_writes():
    """Order is the whole design. A broken night is evidence and belongs in git and in the
    warehouse, so the assertion must come after the commit and both republishes -- otherwise
    `set -euo pipefail` aborts the job first and throws the evidence away."""
    body = WORKFLOW.read_text()
    guard = body.index("scripts.check_collection")
    assert body.index("git commit") < guard
    assert body.index("scripts/observations.py upload") < guard
    assert body.index("scripts.exports upload") < guard
