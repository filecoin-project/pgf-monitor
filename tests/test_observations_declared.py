"""The (team, function_id, metric) join contract, guarded at the write and over the committed table.

`docs/public-datasets.md` promises that triple is "the identity of a monitored commitment, and it
is stable". It wasn't: 1,269 rows landed under names no manifest declares, and nothing noticed
because `fpm.observations` accepted whatever it was handed and the mart's inner join dropped the
rows silently (OSO-5005).

Two fences, because there are two ways a row reaches the CSV. `fpm observe` goes through
`append_observations`, which now refuses. The backfill in `scripts/observations.py` calls `merge`
and `save_rows` directly and bypasses it entirely -- and the backfill is what wrote most of the
1,269. So the second fence is an invariant over the committed file, which catches a new orphan
whichever path wrote it.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from fpm.observations import (
    CSV_PATH,
    UndeclaredTriple,
    append_observations,
    declared_triples,
    undeclared,
)
from fpm.observe import Observation

# The registry was reconciled on 2026-08-24 (PRs 46 and 47). Every undeclared row predates it, and
# nothing has written one since. A date rather than a count, so declaring a legitimate new metric
# doesn't require editing this test -- only a NEW orphan does, which is the thing worth failing on.
RECONCILED_ON = "2026-08-24"

DECLARED = ("chainsafe", "forest-release-cadence", "avg_days_between_releases")
UNDECLARED = ("chainsafe", "network-uptime", "uptime_ratio")


def _obs(triple, **kwargs):
    team, function_id, metric = triple
    return Observation(
        observed_at="2026-09-14",
        team=team,
        function_id=function_id,
        metric=metric,
        observed_value=1.0,
        method="nightly",
        **kwargs,
    )


def test_undeclared_lists_only_what_the_registry_does_not_carry():
    declared = {DECLARED}
    rows = [
        {"team": t, "function_id": f, "metric": m} for t, f, m in (DECLARED, UNDECLARED, UNDECLARED)
    ]
    assert undeclared(rows, declared) == [UNDECLARED]


def test_append_refuses_a_triple_the_registry_never_declares(tmp_path):
    path = tmp_path / "observations.csv"
    with pytest.raises(UndeclaredTriple) as excinfo:
        append_observations([_obs(UNDECLARED)], path, declared={DECLARED})
    # The message has to name the offender: the whole failure mode is a write nobody could see.
    assert "network-uptime" in str(excinfo.value)
    assert not path.exists(), "a refused write must not leave a partial table behind"


def test_append_accepts_a_declared_triple(tmp_path):
    path = tmp_path / "observations.csv"
    rows = append_observations([_obs(DECLARED)], path, declared={DECLARED})
    assert len(rows) == 1
    assert path.exists()


def test_allow_undeclared_is_an_explicit_escape_hatch(tmp_path):
    path = tmp_path / "observations.csv"
    rows = append_observations([_obs(UNDECLARED)], path, allow_undeclared=True)
    assert len(rows) == 1


def test_declared_triples_reads_adopted_and_draft():
    """A draft's metric is declared. Refusing it would stop a team being measured in exactly the
    window the draft exists for -- staged, monitored, appendix not yet signed."""
    adopted_only = declared_triples(drafts_dir="does/not/exist")
    with_drafts = declared_triples()
    assert adopted_only < with_drafts, "drafts must widen the declared set, not replace it"


def test_no_undeclared_reading_has_landed_since_the_registry_was_reconciled():
    """The invariant fence. Catches a new orphan from any write path, including the backfill.

    The 1,269 historical rows are allowed through by date. A new one is not.
    """
    rows = list(csv.DictReader(Path(CSV_PATH).open()))
    declared = declared_triples()
    offenders = sorted(
        {
            (r["team"], r["function_id"], r["metric"], r["observed_at"][:10])
            for r in rows
            if (r["team"], r["function_id"], r["metric"]) not in declared
            and r["observed_at"][:10] > RECONCILED_ON
        }
    )
    assert offenders == [], (
        f"{len(offenders)} reading(s) written after {RECONCILED_ON} under a triple the registry "
        f"does not declare:\n" + "\n".join(f"  {o}" for o in offenders) + "\n"
        "Declare the metric on its function, or correct the name the writer emits."
    )
