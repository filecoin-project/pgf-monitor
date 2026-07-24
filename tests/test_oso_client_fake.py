from fpm.oso.client import FakeOsoClient, RunInfo


def test_create_find_and_reuse():
    c = FakeOsoClient()
    assert c.find_dataset("org", "ds") is None
    ds = c.create_dataset("org", "ds", "DS")
    assert c.find_dataset("org", "ds") == ds


def test_run_lifecycle_and_rows():
    rows = [{"tvl": 5, "date": 2, "_dlt_load_id": "L", "_dlt_id": "a"}]
    c = FakeOsoClient(run_status="SUCCESS", query_rows=rows)
    ds = c.create_dataset("org", "ds", "DS")
    c.attach_rest_config(ds, {"client": {"base_url": "u"}})
    run_id = c.trigger_run(ds)
    runs = c.get_runs(ds)
    assert runs[-1].run_id == run_id and runs[-1].status == "SUCCESS"
    assert c.table_full_name(ds) is not None
    assert c.query("SELECT 1") == rows


def test_failed_run_status():
    c = FakeOsoClient(run_status="FAILED")
    ds = c.create_dataset("org", "ds", "DS")
    c.trigger_run(ds)
    assert c.get_runs(ds)[-1].status == "FAILED"


def test_delete_removes_dataset():
    c = FakeOsoClient()
    ds = c.create_dataset("org", "ds", "DS")
    c.delete_dataset(ds)
    assert c.find_dataset("org", "ds") is None


def test_run_info_is_a_model():
    r = RunInfo(run_id="r", status="SUCCESS")
    assert r.run_id == "r"
