from fpm.land import FakeStaticModelClient, StaticModelSink, land, verdict_rows


def test_sink_publish_sequence_and_public_grant(sample_bundle):
    client = FakeStaticModelClient()
    sink = StaticModelSink(client, org_id="org")
    model_id = sink.publish("filpgf_public", verdict_rows([sample_bundle()])[0], public=True)
    assert model_id in client.models
    assert client.uploaded[model_id].startswith("recommendation_id,")  # CSV header
    assert model_id in client.granted_public
    assert client.ran  # a run was requested


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
