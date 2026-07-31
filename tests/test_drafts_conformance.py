"""Every checked-in draft stays promotable-shaped: schema-valid after the x_draft strip,
catalogued kernel triples, valid transform SQL, translatable http-json configs.
Allowlist membership is deliberately NOT enforced here (drafts declare their additions)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from fpm.domain import window_for
from fpm.drafts import promotion_problems, split_draft
from fpm.kernel import load_kernel
from fpm.provision import build_ingestion_config

DRAFTS = sorted(Path("registry/drafts").glob("*.yaml"))


@pytest.mark.parametrize("path", DRAFTS, ids=lambda p: p.stem)
def test_draft_is_promotable_shaped(path):
    manifest, _x_draft = split_draft(path)  # raises ManifestError on schema breakage
    problems = promotion_problems(manifest, load_kernel(), allowlist=set())
    hard = [p for p in problems if "allowlist" not in p]
    assert hard == []
    # host allowlisting is validate_draft's job at promotion time, not this test's (see docstring)
    for fn in manifest.functions:
        if fn.source.kind == "http-json":
            cfg = build_ingestion_config(
                fn,
                window_for(fn.sla.cadence, datetime(2026, 7, 15, tzinfo=timezone.utc)),
                manifest.team,
            )
            assert cfg is not None


# NOTE: the 2026-07-15 pre-populated drafts were all promoted into registry/ proper;
# the drafts dir may legitimately be empty until the next batch of proposals.
