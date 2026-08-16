from datetime import datetime, timezone
from pathlib import Path

from fpm.manifest import load_manifest
from fpm.observe import observe

AS_OF = datetime(2026, 7, 1, tzinfo=timezone.utc)
FIXTURES = Path("fixtures/responses")
MANIFEST = "tests/fixtures/chainsafe.yaml"


def _observe(**kwargs):
    return observe(manifest_path=MANIFEST, fixtures_dir=FIXTURES, as_of=AS_OF, **kwargs)


def test_one_observation_per_function():
    obs = _observe()
    manifest = load_manifest(MANIFEST)
    assert [o.function_id for o in obs] == [f.function_id for f in manifest.functions]
    assert {o.team for o in obs} == {"chainsafe"}


def test_carries_the_evaluated_sla():
    by_fn = {o.function_id: o for o in _observe()}
    up = by_fn["network-uptime"]
    assert up.outcome == "pass"
    assert up.observed_value is not None
    assert up.note == ""


def test_the_threshold_a_reading_was_judged_against():
    """The threshold moved out of Observation into its own time series; this is its new home."""
    recs = {r.function_id: r for r in thresholds_for(MANIFEST, AS_OF)}
    up = recs["network-uptime"]
    assert (up.threshold_op, up.threshold_value) == (">=", 0.999)


def test_indeterminate_carries_its_reason():
    snap = {o.function_id: o for o in _observe()}["forest-snapshots"]
    assert snap.outcome == "indeterminate"
    assert snap.note  # why it could not be evaluated, for the reviewer


def test_observed_at_is_a_plain_utc_date():
    assert {o.observed_at for o in _observe()} == {"2026-07-01"}


def test_method_labels_provenance():
    assert {o.method for o in _observe(method="replay:api.github.com")} == {"replay:api.github.com"}


def test_progress_fires_as_each_metric_lands():
    """A live run takes tens of minutes; the caller must be able to report during it, not after."""
    seen = []
    out = _observe(on_observation=seen.append)
    assert [o.function_id for o in seen] == [o.function_id for o in out]


def test_a_failing_fetch_does_not_abort_the_batch(monkeypatch):
    """One dead source yields an indeterminate row; the rest of the manifest still runs."""
    from fpm.adapters import fixture

    original = fixture.FixtureAdapter.fetch
    calls = {"n": 0}

    def boom(self, fn, team, window):
        calls["n"] += 1
        if fn.function_id == "network-uptime":
            raise RuntimeError("source unreachable")
        return original(self, fn, team, window)

    monkeypatch.setattr(fixture.FixtureAdapter, "fetch", boom)
    by_fn = {o.function_id: o for o in _observe()}
    assert calls["n"] == 2
    assert by_fn["network-uptime"].outcome == "indeterminate"
    assert "source unreachable" in by_fn["network-uptime"].note
    assert by_fn["network-uptime"].observed_value is None


def test_review_and_observe_agree_on_the_number(tmp_path):
    """The reviewed value and the recorded value come from one code path, so they cannot drift."""
    from fpm.domain import ApprovalDecision
    from fpm.pipeline import run_review
    from fpm.store import JsonlRecordStore
    from fpm.synthesize import FakeReviewSynthesizer

    bundles = run_review(
        manifest_path=MANIFEST,
        fixtures_dir=FIXTURES,
        synthesizer=FakeReviewSynthesizer(),
        store=JsonlRecordStore(tmp_path),
        decide=lambda r: ApprovalDecision(action="approve", approver="carl"),
        as_of=AS_OF,
    )
    reviewed = {b.recommendation.function_id: b.dossier.sla_result for b in bundles}
    for o in _observe():
        assert o.observed_value == reviewed[o.function_id].observed
        assert o.outcome == reviewed[o.function_id].outcome


import yaml

from fpm.observe import thresholds_for


def test_thresholds_for_emits_one_record_per_function():
    """One row per function per run, mirroring observations exactly — that parity is what
    makes the render-time join a plain equality rather than an as-of window."""
    recs = thresholds_for(MANIFEST, AS_OF)
    manifest = load_manifest(MANIFEST)
    assert [r.function_id for r in recs] == [f.function_id for f in manifest.functions]
    assert {r.observed_at for r in recs} == {"2026-07-01"}
    assert {r.team for r in recs} == {"chainsafe"}
    assert all(r.source in {"signed-appendix", "to-confirm", "provisional"} for r in recs)


def test_thresholds_for_matches_the_observation_keys():
    """The join key must agree by construction, or compliance silently disappears."""
    obs_keys = {(o.team, o.function_id, o.metric, o.observed_at) for o in _observe()}
    thr_keys = {(r.team, r.function_id, r.metric, r.observed_at) for r in thresholds_for(MANIFEST, AS_OF)}
    assert obs_keys == thr_keys


def test_thresholds_for_carries_none_when_unbound(tmp_path):
    """A function with no agreed SLA still gets a row — the absence is the fact being
    recorded. A missing row would be indistinguishable from a day the monitor did not run."""
    raw = yaml.safe_load(Path(MANIFEST).read_text())
    for f in raw["functions"]:
        f["sla"].pop("threshold", None)
    p = tmp_path / "unbound.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False))
    recs = thresholds_for(p, AS_OF)
    assert recs
    assert all(r.threshold_op is None and r.threshold_value is None for r in recs)
    assert all(r.source == "provisional" for r in recs)


def test_a_failed_ingestion_run_says_so():
    """ "no value in source response" blames the source for a fetch that never completed."""
    from fpm.domain import Claim, MeasurementWindow, Reading, SlaResult
    from fpm.observe import _note

    window = MeasurementWindow(start=AS_OF, end=AS_OF)
    reading = Reading(
        team="t",
        function_id="f",
        metric="m",
        measurement_window=window,
        claim=Claim(
            value=None,
            origin="independent",
            source_ref="https://api.github.com",
            fetched_at=AS_OF,
            evidence=None,
            fetched_by="test",
        ),
        source_metadata={"run_status": "FAILED"},
        adapter="oso",
        adapter_version="0.1.0",
    )
    sla = SlaResult(
        outcome="indeterminate",
        op="<=",
        threshold=1.0,
        observed=None,
        measurement_window=window,
        reason="no value in source response for the measurement window",
    )
    assert _note(reading, sla).startswith("ingestion run FAILED")
