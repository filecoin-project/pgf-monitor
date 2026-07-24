from fpm.cli import run_land_cli
from fpm.land import FakeStaticModelClient, StaticModelSink
from fpm.store import JsonlRecordStore


def test_run_land_cli_lands_bundles_from_store(tmp_path, sample_bundle):
    store = JsonlRecordStore(tmp_path)
    store.save_adjudication(sample_bundle())
    client = FakeStaticModelClient()
    rc = run_land_cli(str(tmp_path), org_id="org", sink=StaticModelSink(client, "org"))
    assert rc == 0
    assert len(client.datasets) == 2  # filpgf_public + filpgf_private
    assert client.granted_public  # public table was granted


def test_run_land_cli_empty_store_is_noop(tmp_path, capsys):
    rc = run_land_cli(str(tmp_path), org_id="org", sink=None)  # no bundles -> never builds a client
    assert rc == 0
    assert "no bundles" in capsys.readouterr().out.lower()
