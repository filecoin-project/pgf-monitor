"""What counts as a change to a commitment — the ONE list, derived from the models.

The diff used to hand-enumerate the fields it compared. Three fields the models grew were
therefore never compared: `team`, `kernel_function` and `source.data_selector`. The last is the
dangerous one: it selects which part of a JSON response dlt reads, so changing it changes the
measured value — and since the live dry-run only exercises functions the diff calls changed, a
`data_selector`-only PR could move a goalpost with neither a warning nor live proof.

So the field set is walked off the pydantic models instead of typed out, every path is classified
here, and `tests/test_governance_fields.py` fails if the models grow a field this map does not
mention. New fields fail CLOSED: `bucket_for` treats anything unknown as material.

`material` vs `trivial` is a narrow judgment: trivial means a change provably cannot alter what
is measured, how the resulting number should be read, or who is accountable for it. Everything
else is material. Note that trivial fields are still DIFFED — they just do not raise a goalpost
flag — so they still select their function for a live dry-run.
"""

from __future__ import annotations

from typing import Any, Literal, get_args, get_origin

from fpm.manifest import FunctionSpec, Manifest

Bucket = Literal["material", "trivial"]

#: Every diffable path in Manifest/FunctionSpec, and what a change to it means.
#: Keys use the model's own path (`transform.sql`, not `source.transform.sql`).
FIELD_BUCKETS: dict[str, Bucket] = {
    # --- manifest level
    # The grant recipient. It is in the OSO dataset name and in the key of every observation and
    # threshold row, so renaming it re-points every measurement this manifest makes.
    "team": "material",
    # Who to ping. Not who is funded, and not part of any measurement — the accountable party is
    # `team`. Eleven manifests still carry an @TODO placeholder here awaiting a handle.
    "maintainers": "trivial",
    # --- function identity and kernel placement
    "function_id": "material",
    "origin": "material",  # lineage of the commitment: oso / karma / external-pr
    "kernel_id": "material",  # which kernel function this SLA evidences
    "tier": "material",
    "category": "material",
    "sub_category": "material",
    # who is paid, and what code the work covers: two facts, two fields, both material
    "funded_project_oso_slug": "material",
    "repos": "material",
    # --- the commitment
    # Prose restating the SLA. Does not change the number or the bar; a wording fix should not
    # read as a moved goalpost. Still diffed, so it still triggers a dry-run.
    "sla.statement": "trivial",
    "sla.metric": "material",
    "sla.threshold_op": "material",
    "sla.threshold_value": "material",
    "sla.threshold_source": "material",  # signed-appendix vs provisional is a real distinction
    "sla.cadence": "material",
    # --- where the number comes from
    "source.adapter": "material",
    "source.kind": "material",
    "source.endpoint": "material",
    "source.query": "material",
    "source.base_url": "material",
    "source.method": "material",
    "source.params": "material",
    "source.paginator": "material",
    "source.data_selector": "material",  # selects the part of the response that is read
    "source.max_table_nesting": "material",
    "source.auth_secret_ref": "material",
    "source.fixture": "material",
    # --- how the number is derived
    "source.extract.path": "material",
    "source.extract.column": "material",
    "source.extract.cast": "material",
    "source.extract.unit": "material",
    "source.extract.reduce": "material",
    "source.extract.timestamp_column": "material",
    "source.extract.derive": "material",
    "source.extract.column2": "material",
    "transform.sql": "material",
}

#: Walked, not listed: a container whose leaves are classified individually.
_CONTAINERS = ("sla", "source", "source.extract", "transform")

#: Structure, not a commitment: functions are diffed per function_id by fpm.governance.diff.
_STRUCTURAL = ("functions",)


def _is_model(annotation: Any) -> type | None:
    """The model class behind an annotation, unwrapping Optional/unions."""
    candidates = [annotation, *get_args(annotation)] if get_origin(annotation) else [annotation]
    for c in candidates:
        if isinstance(c, type) and hasattr(c, "model_fields"):
            return c
    return None


def _walk(model: type, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    for name, field in model.model_fields.items():
        path = f"{prefix}{name}"
        if path in _STRUCTURAL:
            continue
        nested = _is_model(field.annotation)
        if nested is not None:
            paths |= _walk(nested, f"{path}.")
        else:
            paths.add(path)
    return paths


def manifest_field_paths() -> set[str]:
    """Every leaf path a manifest can carry, walked off the models themselves."""
    return _walk(Manifest) | _walk(FunctionSpec)


def unclassified_field_paths() -> set[str]:
    return manifest_field_paths() - set(FIELD_BUCKETS)


def bucket_for(path: str) -> Bucket:
    """Fail closed: a field nobody classified is material."""
    return FIELD_BUCKETS.get(path, "material")


def function_values(fn: FunctionSpec) -> dict[str, Any]:
    """path -> value for one function. A path under a None container is ABSENT, not None, so
    dropping a whole `extract`/`transform` block reads as its fields changing."""
    out: dict[str, Any] = {}
    for path in FIELD_BUCKETS:
        if path in ("team", "maintainers"):
            continue
        obj: Any = fn
        for part in path.split("."):
            obj = getattr(obj, part, None)
            if obj is None:
                break
        else:
            out[path] = obj
            continue
        # a leaf that is legitimately None still counts as present when its parents exist
        parents, _, leaf = path.rpartition(".")
        holder: Any = fn
        for part in filter(None, parents.split(".")):
            holder = getattr(holder, part, None)
            if holder is None:
                break
        if holder is not None and hasattr(holder, leaf):
            out[path] = getattr(holder, leaf)
    return out


def changed_field_paths(old: FunctionSpec, new: FunctionSpec) -> set[str]:
    ov, nv = function_values(old), function_values(new)
    return {p for p in ov.keys() | nv.keys() if ov.get(p) != nv.get(p)}
