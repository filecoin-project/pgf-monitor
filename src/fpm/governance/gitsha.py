"""Resolve the commit that governs a manifest. Requires full history (fetch-depth 0) in CI."""

from __future__ import annotations

import subprocess
from pathlib import Path


def git_manifest_sha(path: str | Path, repo_root: str | Path | None = None) -> str:
    root = Path(repo_root) if repo_root else Path.cwd()
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%H", "--", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "uncommitted"
    sha = out.stdout.strip()
    return sha or "uncommitted"
