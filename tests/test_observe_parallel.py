"""The nightly run measures several metrics at once, and nothing downstream may be able to tell.

Each live metric is a whole OSO ingestion job, ~20s on the platform plus polling and two Trino
reads, and nearly all of it is waiting. Measured one at a time, 46 of them took 28-37 minutes
against a 40-minute deadline, and on 2026-10-07 a slow platform night pushed past it and left
8 commitments unattempted. `observe_all` runs them through a thread pool instead.

What concurrency must NOT change, pinned here offline:

- the rows come back in manifest order and function order, whatever order they finished in;
- each manifest is handed to the caller once, complete, as soon as its last metric lands, so a
  killed process still loses only what was in flight;
- a manifest that cannot be measured costs its own rows and nobody else's.

The concurrency itself is proven with a barrier rather than a timer: two fetches that each wait
for the other can only both succeed if they really are in flight together.
"""

import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

import fpm.observe as observe_mod
from fpm.adapters.registry import build_adapters
from fpm.observe import TRUNCATED_NOTE, observe_all

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
FIXTURES = Path("fixtures/responses")
CHAINSAFE = Path("tests/fixtures/chainsafe.yaml")  # 2 functions: network-uptime, forest-snapshots


@pytest.fixture
def two_manifests(tmp_path):
    """chainsafe plus a copy of it under another team, so both measure offline."""
    second = tmp_path / "zzz_second.yaml"
    second.write_text(CHAINSAFE.read_text().replace("team: chainsafe", "team: zzz_second", 1))
    return [CHAINSAFE, second]


def _wrap_fixture_adapter(monkeypatch, before_fetch):
    """Run `before_fetch(fn)` ahead of every real fixture fetch."""

    def patched(*args, **kwargs):
        adapters = build_adapters(*args, **kwargs)
        real = adapters["fixture"]

        class Wrapped:
            name = real.name
            version = real.version

            def fetch(self, fn, team, window):
                before_fetch(fn)
                return real.fetch(fn, team, window)

        adapters["fixture"] = Wrapped()
        return adapters

    monkeypatch.setattr(observe_mod, "build_adapters", patched)


def test_metrics_are_really_in_flight_together(monkeypatch):
    """Each fetch waits at a two-party barrier. One at a time, the first would time out, break
    the barrier, and both readings would come back value-less instead of matching a plain run.
    (Compared against a plain run rather than checking the note: a broken barrier's error has
    an empty message, so `_note` never names it.)"""
    plain, _ = observe_all([CHAINSAFE], FIXTURES, AS_OF)
    barrier = threading.Barrier(2, timeout=5)
    _wrap_fixture_adapter(monkeypatch, lambda fn: barrier.wait())

    out, failed = observe_all([CHAINSAFE], FIXTURES, AS_OF, workers=2)

    assert failed == []
    assert plain[0].observed_value is not None
    assert [(o.observed_value, o.note) for o in out] == [(o.observed_value, o.note) for o in plain]


def test_rows_come_back_in_function_order_whatever_order_they_finished(monkeypatch):
    """The first function is made the slowest, so it finishes last; the output must not care."""
    delays = {"network-uptime": 0.3, "forest-snapshots": 0.0}
    _wrap_fixture_adapter(monkeypatch, lambda fn: time.sleep(delays[fn.function_id]))

    landed = []
    out, _ = observe_all(
        [CHAINSAFE],
        FIXTURES,
        AS_OF,
        workers=2,
        on_observation=lambda obs, seconds: landed.append(obs.function_id),
    )

    assert landed == ["forest-snapshots", "network-uptime"]  # completion order
    assert [o.function_id for o in out] == ["network-uptime", "forest-snapshots"]


def test_the_progress_callback_carries_how_long_the_metric_took(monkeypatch):
    _wrap_fixture_adapter(monkeypatch, lambda fn: time.sleep(0.05))
    seconds = []
    observe_all(
        [CHAINSAFE], FIXTURES, AS_OF, workers=2, on_observation=lambda o, s: seconds.append(s)
    )
    assert len(seconds) == 2 and all(s >= 0.05 for s in seconds)


def test_each_manifest_is_handed_over_once_complete_and_alone(two_manifests):
    handed = []
    out, failed = observe_all(
        two_manifests,
        FIXTURES,
        AS_OF,
        workers=4,
        on_manifest=lambda path, got: handed.append((path.stem, [o.team for o in got])),
    )

    assert failed == []
    assert sorted(handed) == [
        ("chainsafe", ["chainsafe", "chainsafe"]),
        ("zzz_second", ["zzz_second", "zzz_second"]),
    ]
    assert [o.team for o in out] == ["chainsafe", "chainsafe", "zzz_second", "zzz_second"]


def test_a_manifest_that_will_not_load_costs_only_its_own_rows(two_manifests, tmp_path):
    broken = tmp_path / "broken.yaml"
    broken.write_text("team: broken\nfunctions: not-a-list\n")
    handed = []

    out, failed = observe_all(
        [broken, *two_manifests],
        FIXTURES,
        AS_OF,
        workers=4,
        on_manifest=lambda path, got: handed.append(path.stem),
    )

    assert [path.stem for path, _ in failed] == ["broken"]
    assert sorted(handed) == ["chainsafe", "zzz_second"]
    assert {o.team for o in out} == {"chainsafe", "zzz_second"}


def test_a_function_raising_past_measure_fails_its_manifest_not_the_run(monkeypatch, two_manifests):
    """`measure` isolates fetch errors, so this takes something after it -- the age guard,
    say -- raising. The manifest is reported failed and handed to nobody, rather than
    persisting with a hole in it."""
    real = observe_mod.observe_function

    def flaky(fn, team, *args, **kwargs):
        if team == "zzz_second" and fn.function_id == "forest-snapshots":
            raise RuntimeError("boom")
        return real(fn, team, *args, **kwargs)

    monkeypatch.setattr(observe_mod, "observe_function", flaky)
    handed = []

    out, failed = observe_all(
        two_manifests,
        FIXTURES,
        AS_OF,
        workers=4,
        on_manifest=lambda path, got: handed.append(path.stem),
    )

    assert [(path.stem, str(exc)) for path, exc in failed] == [("zzz_second", "boom")]
    assert handed == ["chainsafe"]
    assert {o.team for o in out} == {"chainsafe"}


def test_once_the_deadline_passes_nothing_new_starts(two_manifests):
    """Checked as each function starts, and sticky: the first refusal ends the night for every
    function not yet started, even if a later check would have said yes."""
    answers = iter([True, False, True, True])

    out, _ = observe_all(
        two_manifests, FIXTURES, AS_OF, workers=1, should_continue=lambda: next(answers)
    )

    assert TRUNCATED_NOTE not in out[0].note
    assert all(TRUNCATED_NOTE in o.note for o in out[1:])


# ------------------------------------------------------------------- retries


def _scripted(monkeypatch, failures: dict[str, int], calls: list):
    """Each function fails (retryably) its first `failures[function_id]` attempts, then reads.

    Records every attempt in `calls` as (team, function_id), in the order attempts start.
    """
    real = observe_mod.observe_function
    seen: dict[tuple[str, str], int] = {}
    lock = threading.Lock()

    def fake(fn, team, *args, **kwargs):
        key = (team, fn.function_id)
        with lock:
            calls.append(key)
            seen[key] = seen.get(key, 0) + 1
            n = seen[key]
        obs, _ = real(fn, team, *args, **kwargs)
        if n <= failures.get(fn.function_id, 0):
            return obs.model_copy(update={"note": f"failed attempt {n}"}), True
        return obs, False

    monkeypatch.setattr(observe_mod, "observe_function", fake)


def test_retries_wait_until_every_function_has_had_its_first_attempt(monkeypatch, two_manifests):
    calls = []
    _scripted(monkeypatch, {"network-uptime": 1}, calls)

    observe_all(two_manifests, FIXTURES, AS_OF, workers=1, retries=2)

    firsts = {
        ("chainsafe", "network-uptime"),
        ("chainsafe", "forest-snapshots"),
        ("zzz_second", "network-uptime"),
        ("zzz_second", "forest-snapshots"),
    }
    assert set(calls[:4]) == firsts
    assert sorted(calls[4:]) == [("chainsafe", "network-uptime"), ("zzz_second", "network-uptime")]


def test_a_retry_that_succeeds_replaces_the_failure(monkeypatch):
    calls, retried, landed = [], [], []
    _scripted(monkeypatch, {"network-uptime": 2}, calls)

    out, _ = observe_all(
        [CHAINSAFE],
        FIXTURES,
        AS_OF,
        workers=2,
        retries=2,
        on_retry=lambda obs, s, attempt: retried.append(attempt),
        on_observation=lambda obs, s: landed.append(obs.function_id),
    )

    assert calls.count(("chainsafe", "network-uptime")) == 3
    assert retried == [1, 2]
    assert sorted(landed) == ["forest-snapshots", "network-uptime"]  # once each, final only
    assert "failed attempt" not in out[0].note


def test_retries_stop_at_the_limit_and_the_last_failure_is_the_row(monkeypatch):
    calls = []
    _scripted(monkeypatch, {"network-uptime": 99}, calls)

    out, _ = observe_all([CHAINSAFE], FIXTURES, AS_OF, workers=2, retries=2)

    assert calls.count(("chainsafe", "network-uptime")) == 3  # first attempt + 2 retries
    assert out[0].note == "failed attempt 3"


def test_no_retries_unless_asked(monkeypatch):
    calls = []
    _scripted(monkeypatch, {"network-uptime": 99}, calls)

    out, _ = observe_all([CHAINSAFE], FIXTURES, AS_OF, workers=2)

    assert calls.count(("chainsafe", "network-uptime")) == 1
    assert out[0].note == "failed attempt 1"


def test_a_retry_the_deadline_stops_keeps_the_failed_attempt(monkeypatch):
    """The function WAS attempted; calling it unattempted would hide a real failure."""
    calls = []
    _scripted(monkeypatch, {"network-uptime": 99}, calls)
    answers = iter([True, True, False])  # both first attempts start; the retry does not

    out, _ = observe_all(
        [CHAINSAFE], FIXTURES, AS_OF, workers=1, retries=2, should_continue=lambda: next(answers)
    )

    assert calls.count(("chainsafe", "network-uptime")) == 1
    assert out[0].note == "failed attempt 1"
    assert TRUNCATED_NOTE not in out[0].note


def test_a_manifest_waiting_on_a_retry_is_handed_over_once_after_it(monkeypatch, two_manifests):
    calls, handed = [], []
    _scripted(monkeypatch, {"network-uptime": 1}, calls)

    observe_all(
        two_manifests,
        FIXTURES,
        AS_OF,
        workers=2,
        retries=2,
        on_manifest=lambda path, got: handed.append((path.stem, [o.note for o in got])),
    )

    assert sorted(stem for stem, _ in handed) == ["chainsafe", "zzz_second"]
    assert all("failed attempt" not in note for _, notes in handed for note in notes)


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ({"fetch_error": ""}, True),  # an exception with an empty message still counts
        ({"run_status": "FAILED"}, True),
        ({"run_status": "CANCELED"}, True),
        ({"run_status": "SUCCESS", "stale_load": "rows were loaded ..."}, True),  # consumed it
        ({"run_status": "TIMEOUT"}, False),  # still running; a second run would race it
        ({"run_status": "SUCCESS"}, False),  # the source answered, with or without a value
        ({"sql_error": "sql result is not numeric"}, False),  # same answer every time
        ({}, False),
    ],
)
def test_what_counts_as_a_retryable_failure(metadata, expected):
    from fpm.domain import window_for
    from fpm.manifest import load_manifest
    from fpm.observe import error_reading, retryable

    fn = load_manifest(CHAINSAFE).functions[0]
    reading = error_reading(fn, "chainsafe", window_for(fn.sla.cadence, AS_OF), RuntimeError())
    assert retryable(reading.model_copy(update={"source_metadata": metadata})) is expected
