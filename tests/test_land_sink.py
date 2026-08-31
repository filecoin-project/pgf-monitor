from fpm.land import (
    FakeStaticModelClient,
    StaticModelSink,
    UnadjudicatedVerdictError,
    land,
    verdict_rows,
)


def test_sink_publish_sequence_and_public_grant(sample_bundle):
    client = FakeStaticModelClient()
    sink = StaticModelSink(client, org_id="org")
    model_id = sink.publish("filpgf_public", verdict_rows([sample_bundle()])[0], public=True)
    assert model_id in client.models
    assert client.uploaded[model_id].startswith("recommendation_id,")  # CSV header
    assert model_id in client.granted_public
    # The run must be requested for the model that just received the CSV, not merely for the
    # dataset: CreateStaticModelRunRequestInput requires BOTH ids, and passing the dataset id
    # twice is the shape that silently 400s against the live API.
    assert client.ran == [(client.models[model_id], model_id)]


def test_sink_private_not_granted_public(sample_bundle):
    client = FakeStaticModelClient()
    sink = StaticModelSink(client, org_id="org")
    model_id = sink.publish("filpgf_private", verdict_rows([sample_bundle()])[1], public=False)
    assert model_id not in client.granted_public


def test_land_publishes_both_tables(sample_bundle):
    client = FakeStaticModelClient()
    sink = StaticModelSink(client, org_id="org")
    result = land([sample_bundle()], sink)
    assert set(result) == {"public", "private"}
    # public table got a public grant; private did not
    assert result["public"] in client.granted_public
    assert result["private"] not in client.granted_public
    # the private CSV carries the approver column, the public one does not
    assert "approver" in client.uploaded[result["private"]].splitlines()[0]
    assert "approver" not in client.uploaded[result["public"]].splitlines()[0]


def test_land_dataset_reused_by_name(sample_bundle):
    client = FakeStaticModelClient()
    sink = StaticModelSink(client, org_id="org")
    land([sample_bundle()], sink)
    land([sample_bundle()], sink)  # second land reuses the same datasets, not new ones
    assert len(client.datasets) == 2  # exactly filpgf_public + filpgf_private


def test_republish_reuses_the_static_model(sample_bundle):
    """Landing twice must reuse the model, not try to create it again.

    `land` republishes the SAME two tables on every review. The live client used to call
    createStaticModel unconditionally, which fails with ALREADY_EXISTS on the second land —
    so verdicts could only ever be published once. Caught landing the 2026-08-16 review.
    """
    client = FakeStaticModelClient()
    sink = StaticModelSink(client, org_id="org")
    rows = verdict_rows([sample_bundle()])[0]

    first = sink.publish("filpgf_sla_verdicts", rows, public=True)
    second = sink.publish("filpgf_sla_verdicts", rows, public=True)

    assert first == second, "republish must reuse the existing static model"
    assert len(client.models) == 1, "no duplicate model should be created"


def test_distinct_names_get_distinct_models(sample_bundle):
    """Idempotency keys on (dataset, name) — the public and private tables stay separate."""
    client = FakeStaticModelClient()
    sink = StaticModelSink(client, org_id="org")
    pub_rows, priv_rows = verdict_rows([sample_bundle()])

    pub = sink.publish("filpgf_sla_verdicts", pub_rows, public=True)
    priv = sink.publish("filpgf_sla_verdicts_private", priv_rows, public=False)

    assert pub != priv
    assert len(client.models) == 2


def test_land_refuses_verdicts_that_no_human_adjudicated(sample_bundle):
    """`--dev-auto-approve` stamps approver="dev-auto". Those verdicts are a development
    convenience; letting them reach the public table would make "a human adjudicated this"
    false for rows nobody ever read."""
    import pytest

    client = FakeStaticModelClient()
    sink = StaticModelSink(client, org_id="org")

    with pytest.raises(UnadjudicatedVerdictError) as exc:
        land([sample_bundle(approver="dev-auto")], sink)

    assert "chainsafe" in str(exc.value) and "forest-uptime" in str(exc.value)
    assert not client.models  # refused before publishing anything


def test_land_refuses_the_whole_batch_if_any_verdict_is_unadjudicated(sample_bundle):
    import pytest

    client = FakeStaticModelClient()
    sink = StaticModelSink(client, org_id="org")
    bundles = [sample_bundle(rid="rec-1"), sample_bundle(rid="rec-2", approver="dev-auto")]

    with pytest.raises(UnadjudicatedVerdictError):
        land(bundles, sink)

    assert not client.models
