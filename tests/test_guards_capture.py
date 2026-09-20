"""Refusing a reading is the only moment the evidence behind it exists.

The fault behind `pipeline_success_age_days` fired four times across three weeks and was never
root-caused, because by the time anyone looked the ingestion table had been overwritten
(`write_disposition: replace`) and OSO's run logs had aged out. The guard nulls the value at
exactly the instant the bad rows are in hand -- so it writes them down first.

The point of the capture is `oso_run_ref`. The rows alone cannot distinguish "GitHub served a bad
response" from "something between GitHub and the table produced one"; the run identifiers are what
let someone ask OSO what its ingestion actually did that night.
"""

from __future__ import annotations

import json

from fpm.domain import Claim, EvidenceRef, MeasurementWindow, OsoRunRef, Reading
from fpm.guards import CAPTURE_DIR_ENV, MAX_CAPTURED_ROWS, capture_dir
from fpm.manifest import ExtractSpec, FunctionSpec, SlaSpec, SourceSpec
from fpm.observe import Observation, apply_age_guard

WINDOW = MeasurementWindow(start="2026-09-12T00:00:00+00:00", end="2026-09-13T00:00:00+00:00")
KEY = (
    "filecoin-data-portal",
    "network-data-portal-pipeline-freshness",
    "pipeline_success_age_days",
)


def _reading(rows, run_ref=True):
    return Reading(
        team=KEY[0],
        function_id=KEY[1],
        metric=KEY[2],
        measurement_window=WINDOW,
        claim=Claim(
            value=17.6292,
            origin="independent",
            source_ref="https://api.github.com",
            fetched_at="2026-09-13T05:23:00+00:00",
            evidence=EvidenceRef(
                raw_payload_hash=None,
                canonical_payload_hash="c" * 64,
                request_fingerprint="d" * 64,
                evidence_bundle_hash="b" * 64,
                oso_run_ref=OsoRunRef(
                    run_id="run-123",
                    status="SUCCESS",
                    dlt_load_id="load-456",
                    logs_url="https://oso.xyz/logs/run-123",
                )
                if run_ref
                else None,
            ),
            fetched_by="oso@1",
        ),
        source_metadata={"kind": "http-json", "run_status": "SUCCESS"},
        adapter="oso",
        adapter_version="1",
        raw_rows=rows,
    )


def _fn(derive="age_days"):
    return FunctionSpec(
        function_id=KEY[1],
        tier="essential",
        sla=SlaSpec(statement="s", metric=KEY[2], cadence="daily"),
        source=SourceSpec(
            adapter="oso", kind="http-json", extract=ExtractSpec(column="created_at", derive=derive)
        ),
    )


def _obs(value=17.6292):
    return Observation(
        observed_at="2026-09-13",
        team=KEY[0],
        function_id=KEY[1],
        metric=KEY[2],
        observed_value=value,
        method="nightly",
    )


PRIOR = {KEY: ("2026-09-12", 0.5102)}
STALE = [{"created_at": "2026-08-26T14:36:00Z", "id": 1}, {"created_at": "2026-07-21T10:00:00Z"}]


def test_a_refusal_writes_the_rows_and_the_run_reference(tmp_path):
    apply_age_guard(_fn(), _obs(), PRIOR, reading=_reading(STALE), capture_dir=tmp_path)
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    rec = json.loads(files[0].read_text())
    assert rec["rows"] == STALE
    # The whole point: the handle on OSO's side of the fetch.
    assert rec["oso_run_ref"]["run_id"] == "run-123"
    assert rec["oso_run_ref"]["dlt_load_id"] == "load-456"
    assert rec["refused_value"] == 17.6292
    assert (rec["previous_day"], rec["previous_value"]) == ("2026-09-12", 0.5102)
    assert "impossible age growth" in rec["reason"]


def test_the_filename_identifies_the_metric_and_the_night(tmp_path):
    apply_age_guard(_fn(), _obs(), PRIOR, reading=_reading(STALE), capture_dir=tmp_path)
    assert [p.name for p in tmp_path.glob("*.json")] == [
        "2026-09-13_filecoin-data-portal_pipeline_success_age_days.json"
    ]


def test_the_reading_is_still_refused_when_capture_is_impossible(tmp_path):
    """Diagnostics must never cost us the fix. An unwritable directory is not a reason to publish
    a number we can prove false, nor to crash the night's collection."""
    blocked = tmp_path / "nope"
    blocked.write_text("i am a file, not a directory")
    obs = _obs()
    apply_age_guard(_fn(), obs, PRIOR, reading=_reading(STALE), capture_dir=blocked)
    assert obs.observed_value is None
    assert obs.outcome == "indeterminate"


def test_nothing_is_written_when_the_reading_is_good(tmp_path):
    apply_age_guard(_fn(), _obs(0.5489), PRIOR, reading=_reading(STALE), capture_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_a_missing_run_reference_still_captures_the_rows(tmp_path):
    """An oso-sql metric has no ingestion run. The rows are still worth having."""
    apply_age_guard(
        _fn(), _obs(), PRIOR, reading=_reading(STALE, run_ref=False), capture_dir=tmp_path
    )
    rec = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert rec["oso_run_ref"] is None and rec["rows"] == STALE


def test_a_runaway_source_cannot_write_an_unbounded_file(tmp_path):
    rows = [{"created_at": "2026-08-26T14:36:00Z", "n": i} for i in range(MAX_CAPTURED_ROWS + 50)]
    apply_age_guard(_fn(), _obs(), PRIOR, reading=_reading(rows), capture_dir=tmp_path)
    rec = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert len(rec["rows"]) == MAX_CAPTURED_ROWS
    assert rec["rows_truncated"] is True
    assert rec["row_count"] == MAX_CAPTURED_ROWS + 50  # the true count survives the truncation


def test_capture_is_skipped_entirely_without_a_reading(tmp_path):
    """`apply_age_guard` is called directly in tests and by older callers; it must still refuse."""
    obs = _obs()
    apply_age_guard(_fn(), obs, PRIOR, capture_dir=tmp_path)
    assert obs.observed_value is None
    assert list(tmp_path.iterdir()) == []


def test_the_capture_directory_is_configurable_and_never_under_data(monkeypatch):
    """`data/` is the published system of record; a capture is diagnostic material, not a fact."""
    monkeypatch.delenv(CAPTURE_DIR_ENV, raising=False)
    assert "data" not in capture_dir().parts
    monkeypatch.setenv(CAPTURE_DIR_ENV, "/tmp/elsewhere")
    assert str(capture_dir()) == "/tmp/elsewhere"
    assert str(capture_dir("/tmp/explicit")) == "/tmp/explicit"  # argument beats environment


def test_captures_are_gitignored():
    """They must never reach the public repo by accident."""
    assert "evidence/" in open(".gitignore").read().splitlines()


def test_rows_never_reach_a_dump_of_the_reading():
    """`raw_rows` is excluded, so it cannot leak into an evidence bundle, a store record or a CSV."""
    dumped = _reading(STALE).model_dump(mode="json")
    assert "raw_rows" not in dumped
    assert "2026-08-26T14:36:00Z" not in json.dumps(dumped)


def test_the_capture_records_the_url_that_was_asked_for(tmp_path):
    """Without the endpoint there is nothing for a control fetch to repeat, and the capture can
    say WHAT came back but never WHERE it came from."""
    fn = _fn()
    fn.source.endpoint = "https://api.github.com/repos/x/y/actions/workflows/p.yml/runs?per_page=30"
    apply_age_guard(fn, _obs(), PRIOR, reading=_reading(STALE), capture_dir=tmp_path)
    rec = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert rec["endpoint"].endswith("per_page=30")


def test_the_control_fetch_script_is_quarantined_from_the_test_suite():
    """It makes live network calls. Tests are offline-deterministic, so nothing may import it."""
    import pathlib

    path = pathlib.Path("scripts/capture_control_fetch.py")
    assert path.exists()
    offenders = [
        p.name
        for p in pathlib.Path("tests").glob("*.py")
        if "capture_control_fetch" in p.read_text() and p.name != "test_guards_capture.py"
    ]
    assert not offenders, f"live script imported by tests: {offenders}"


def test_the_filtered_variant_restores_exactly_the_shape_that_failed():
    """The comparison is only meaningful if the variant is the query the episodes came through."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("ccf", "scripts/capture_control_fetch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    got = mod._filtered_variant("https://api.github.com/repos/x/y/runs?per_page=30")
    assert "status=success" in got and "per_page=30" in got
    # and it must not stack a second copy when one is already there
    assert mod._filtered_variant(got).count("status=success") == 1


def test_the_published_page_check_is_quarantined_too():
    """Live network, like the smokes. Tests stay offline-deterministic."""
    import pathlib

    assert pathlib.Path("scripts/check_published_page.py").exists()
    offenders = [
        p.name
        for p in pathlib.Path("tests").glob("*.py")
        if "check_published_page" in p.read_text() and p.name != "test_guards_capture.py"
    ]
    assert not offenders, f"live script imported by tests: {offenders}"


def test_how_publishing_works_is_documented_where_someone_would_look():
    """Publishing went automatic on 2026-09-20; the README has to say so, and has to keep saying
    that a hash cannot see data staleness -- that asymmetry is the whole reason the check grew a
    second half, and it is the thing a reader will otherwise assume away."""
    import pathlib

    readme = pathlib.Path("dashboards/README.md").read_text()
    assert "Publishing is automatic" in readme
    assert "sourceHash" in readme
    assert "publish_page.py" in readme
    assert "blind to DATA staleness" in readme
