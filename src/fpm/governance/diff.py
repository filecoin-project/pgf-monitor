"""Pure, per-field manifest diff. No git, no IO."""

from __future__ import annotations

from typing import Any, Literal

from fpm.domain import _Model
from fpm.manifest import FunctionSpec, Manifest

_EXTRACT_FIELDS = (
    "path",
    "column",
    "cast",
    "unit",
    "reduce",
    "timestamp_column",
    "derive",
    "column2",
)


class Change(_Model):
    function_id: str
    field_path: str
    kind: Literal["added", "removed", "modified"]
    old: Any = None
    new: Any = None


def _fields(fn: FunctionSpec) -> dict[str, Any]:
    s, src = fn.sla, fn.source
    d: dict[str, Any] = {
        "tier": fn.tier,
        "category": fn.category,
        "sub_category": fn.sub_category,
        "oso_project_slug": fn.oso_project_slug,
        "sla.metric": s.metric,
        "sla.threshold_op": s.threshold_op,
        "sla.threshold_value": s.threshold_value,
        "sla.threshold_source": s.threshold_source,
        "sla.cadence": s.cadence,
        "sla.statement": s.statement,
        "source.kind": src.kind,
        "source.base_url": src.base_url,
        "source.endpoint": src.endpoint,
        "source.query": src.query,
        "source.method": src.method,
        "source.params": src.params,
        "source.paginator": src.paginator,
        "source.auth_secret_ref": src.auth_secret_ref,
        "source.fixture": src.fixture,
        "source.adapter": src.adapter,
        "source.max_table_nesting": src.max_table_nesting,
    }
    if src.extract is not None:
        for k in _EXTRACT_FIELDS:
            d[f"source.extract.{k}"] = getattr(src.extract, k)
    if fn.transform is not None:
        d["source.transform.sql"] = fn.transform.sql
    return d


def manifest_diff(old: Manifest, new: Manifest) -> list[Change]:
    changes: list[Change] = []
    old_fns = {f.function_id: f for f in old.functions}
    new_fns = {f.function_id: f for f in new.functions}

    for fid in old_fns.keys() - new_fns.keys():
        changes.append(Change(function_id=fid, field_path="function", kind="removed"))
    for fid in new_fns.keys() - old_fns.keys():
        changes.append(Change(function_id=fid, field_path="function", kind="added"))
    for fid in old_fns.keys() & new_fns.keys():
        of, nf = _fields(old_fns[fid]), _fields(new_fns[fid])
        for path in of.keys() | nf.keys():
            ov, nv = of.get(path), nf.get(path)
            if ov != nv:
                changes.append(
                    Change(function_id=fid, field_path=path, kind="modified", old=ov, new=nv)
                )

    if old.maintainers != new.maintainers:
        changes.append(
            Change(
                function_id="",
                field_path="maintainers",
                kind="modified",
                old=old.maintainers,
                new=new.maintainers,
            )
        )
    return changes
