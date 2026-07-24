import subprocess
from pathlib import Path

from fpm.governance.gitsha import git_manifest_sha


def test_returns_sha_for_committed_file(tmp_path: Path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    f = tmp_path / "m.yaml"
    f.write_text("team: x\n")
    subprocess.run(["git", "add", "m.yaml"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "add"], cwd=tmp_path, check=True)
    sha = git_manifest_sha("m.yaml", repo_root=tmp_path)
    assert len(sha) == 40 and sha != "uncommitted"


def test_uncommitted_for_unknown_path(tmp_path: Path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    assert git_manifest_sha("nope.yaml", repo_root=tmp_path) == "uncommitted"
