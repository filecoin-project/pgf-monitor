from fpm.cli import main


def test_cli_dev_auto_approve(tmp_path, capsys):
    code = main(
        [
            "review",
            "chainsafe",
            "--manifest",
            "tests/fixtures/chainsafe.yaml",
            "--store",
            str(tmp_path),
            "--as-of",
            "2026-07-01",
            "--dev-auto-approve",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "network-uptime" in out and "pass" in out and "meeting" in out
    assert "forest-snapshots" in out and "indeterminate" in out and "pending_review" in out
