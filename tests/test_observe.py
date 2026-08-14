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
    assert up.sla_outcome == "pass"
    assert up.observed_value is not None
    assert (up.threshold_op, up.threshold_value) == (">=", 0.999)
    assert up.note == ""


def test_indeterminate_carries_its_reason():
    snap = {o.function_id: o for o in _observe()}["forest-snapshots"]
    assert snap.sla_outcome == "indeterminate"
    assert snap.note  # why it could not be evaluated, for the reviewer


def test_observed_at_is_a_plain_utc_date():
    assert {o.observed_at for o in _observe()} == {"2026-07-01"}


def test_method_labels_provenance():
    assert {o.method for o in _observe(method="replay:api.github.com")} == {"replay:api.github.com"}


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
    assert by_fn["network-uptime"].sla_outcome == "indeterminate"
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
        assert o.sla_outcome == reviewed[o.function_id].outcome
