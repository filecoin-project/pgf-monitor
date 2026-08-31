"""scripts/observations.py publishes the CSVs. Offline: the OSO client is faked."""


def test_upload_thresholds_targets_its_own_table(monkeypatch):
    """Two tables, two static models. Publishing thresholds into the observations model
    would overwrite the value history with commitments — unrecoverable, since the CSV is
    the system of record for exactly one of them."""
    from scripts import observations as script

    seen = {}

    class FakeClient:
        def __init__(self, **kw):
            pass

        def ensure_static_dataset(self, org_id, name):
            seen["dataset"] = name
            return "ds-1"

        def ensure_static_model(self, org_id, dataset_id, name):
            seen["model"] = name
            return "sm-1"

        def upload_csv(self, model_id, text):
            seen["text"] = text

        def run_static_model(self, dataset_id, static_model_id):
            seen["ran"] = (dataset_id, static_model_id)

        def grant_public(self, model_id):
            seen["public"] = True

    monkeypatch.setenv("OSO_API_KEY", "not-a-real-key")
    monkeypatch.setattr("fpm.oso.static_model.GraphqlStaticModelClient", FakeClient, raising=True)
    script.main(["upload-thresholds", "--oso-org", "35c17c26-4aa8-47ba-ba75-be8fe1e3718c"])
    assert seen["dataset"] == "filpgf_sla_thresholds"
    assert seen["model"] == "filpgf_sla_thresholds"
    assert seen["public"] is True
    assert seen["ran"] == ("ds-1", "sm-1")  # both ids reach the run request
    assert seen["text"].splitlines()[0].startswith("observed_at,team,function_id,metric")
