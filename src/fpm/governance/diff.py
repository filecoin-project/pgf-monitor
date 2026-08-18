"""Pure, per-field manifest diff. No git, no IO.

The field set is NOT enumerated here: it is walked off the models and classified in
fpm.governance.fields, so a field the models grow cannot quietly fall out of the diff — which is
how `team`, `kernel_function` and `source.data_selector` went uncompared. Anything the diff emits
is also what selects functions for the live dry-run, so the two boundaries cannot drift apart.
"""

from __future__ import annotations

from typing import Any, Literal

from fpm.domain import _Model
from fpm.governance.fields import function_values
from fpm.manifest import Manifest


class Change(_Model):
    function_id: str
    field_path: str
    kind: Literal["added", "removed", "modified"]
    old: Any = None
    new: Any = None


def manifest_diff(old: Manifest, new: Manifest) -> list[Change]:
    changes: list[Change] = []
    old_fns = {f.function_id: f for f in old.functions}
    new_fns = {f.function_id: f for f in new.functions}

    for fid in old_fns.keys() - new_fns.keys():
        changes.append(Change(function_id=fid, field_path="function", kind="removed"))
    for fid in new_fns.keys() - old_fns.keys():
        changes.append(Change(function_id=fid, field_path="function", kind="added"))
    for fid in old_fns.keys() & new_fns.keys():
        of, nf = function_values(old_fns[fid]), function_values(new_fns[fid])
        for path in of.keys() | nf.keys():
            ov, nv = of.get(path), nf.get(path)
            if ov != nv:
                changes.append(
                    Change(function_id=fid, field_path=path, kind="modified", old=ov, new=nv)
                )

    # Manifest-level fields carry no function_id. `team` is one of them and it is anything but
    # cosmetic: it names the OSO dataset and keys every observation and threshold row.
    for path, ov, nv in (
        ("team", old.team, new.team),
        ("maintainers", old.maintainers, new.maintainers),
    ):
        if ov != nv:
            changes.append(Change(function_id="", field_path=path, kind="modified", old=ov, new=nv))
    return changes
