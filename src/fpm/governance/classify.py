"""Goalpost rubric. material / new / trivial, direction-aware on thresholds. Pure."""

from __future__ import annotations

from typing import Literal

from fpm.domain import _Model
from fpm.governance.diff import Change
from fpm.manifest import Manifest

_TRIVIAL = {"sla.statement", "maintainers"}


class ClassifiedChange(_Model):
    function_id: str
    field_path: str
    kind: Literal["added", "removed", "modified"]
    old: object = None
    new: object = None
    bucket: Literal["material", "new", "trivial"]
    direction: Literal["loosened", "tightened", "n/a"] = "n/a"
    reason: str


def _direction(op: str, old: float, new: float) -> Literal["loosened", "tightened", "n/a"]:
    if op in (">=", ">"):
        return "loosened" if new < old else "tightened" if new > old else "n/a"
    if op in ("<=", "<"):
        return "loosened" if new > old else "tightened" if new < old else "n/a"
    return "n/a"


def classify(changes: list[Change], new: Manifest) -> list[ClassifiedChange]:
    ops = {f.function_id: f.sla.threshold_op for f in new.functions}
    out: list[ClassifiedChange] = []
    for c in changes:
        base = c.model_dump()
        if c.kind == "added":
            out.append(ClassifiedChange(**base, bucket="new", reason="net-new function/commitment"))
            continue
        if c.kind == "removed":
            out.append(ClassifiedChange(**base, bucket="material", reason="function removed"))
            continue
        if c.field_path in _TRIVIAL:
            out.append(ClassifiedChange(**base, bucket="trivial", reason="non-committal change"))
            continue
        direction: Literal["loosened", "tightened", "n/a"] = "n/a"
        reason = f"{c.field_path} changed"
        if c.field_path == "sla.threshold_value" and c.function_id in ops:
            op = ops[c.function_id]
            if c.old is None:
                # A commitment coming into existence. Bound where it was unbound.
                direction, reason = "tightened", "threshold added: new commitment"
            elif c.new is None:
                # A commitment being withdrawn. Strictly a loosening.
                direction, reason = "loosened", "threshold removed: commitment withdrawn"
            elif op is None:
                reason = "threshold changed"
            else:
                direction = _direction(op, float(c.old), float(c.new))
                reason = f"threshold {direction}" if direction != "n/a" else "threshold changed"
        out.append(ClassifiedChange(**base, bucket="material", direction=direction, reason=reason))
    return out


def has_material(items: list[ClassifiedChange]) -> bool:
    return any(i.bucket == "material" for i in items)
