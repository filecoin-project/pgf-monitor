"""Load and validate the Filecoin Kernel inventory.

The kernel inventory (registry/_kernel.yaml) is the canonical taxonomy of kernel functions that
registry submissions must conform to: a submission names the exact kernel function it evidences
via its slug `id`, and declares the (tier, category, sub_category) slot that function sits in.
Fields: id, tier, category, sub_category, function, value.

`id` is the join key. The display name (`function`) is presentation text and must never be joined
on: it is long, it gets reworded, and two functions once differed only in punctuation. Ids are
immutable once merged, so `load_kernel` refuses duplicates rather than letting two rows fight
over one key.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

from fpm.domain import _Model

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "registry" / "_kernel_schema.json"
_KERNEL_PATH = Path(__file__).resolve().parents[2] / "registry" / "_kernel.yaml"


class KernelError(ValueError):
    """Raised when the kernel inventory fails schema validation or id uniqueness."""


class KernelEntry(_Model):
    id: str
    tier: str
    category: str
    sub_category: str
    function: str
    value: str = ""


class Kernel(_Model):
    entries: list[KernelEntry]


def load_kernel(path: str | Path = _KERNEL_PATH) -> Kernel:
    raw = yaml.safe_load(Path(path).read_text())
    errors = sorted(
        Draft7Validator(json.loads(_SCHEMA_PATH.read_text())).iter_errors(raw),
        key=lambda e: list(e.path),
    )
    if errors:
        raise KernelError("; ".join(e.message for e in errors))
    kernel = Kernel(entries=[KernelEntry(**e) for e in raw["entries"]])
    seen: set[str] = set()
    dupes = sorted({e.id for e in kernel.entries if e.id in seen or seen.add(e.id)})
    if dupes:
        raise KernelError(f"duplicate kernel id(s): {', '.join(dupes)}")
    return kernel


def by_id(kernel: Kernel) -> dict[str, KernelEntry]:
    """The inventory indexed by its join key."""
    return {e.id: e for e in kernel.entries}


def catalogued_triples(kernel: Kernel) -> set[tuple[str, str, str]]:
    return {(e.tier, e.category, e.sub_category) for e in kernel.entries}


#: Reserved `kernel_id`: this metric measures something real that the kernel inventory does not
#: name. Explicit, greppable absence, the same shape as an omitted threshold meaning "measured,
#: not scored". It is deliberately not an inventory id.
NON_KERNEL_ID = "non-kernel"


def conformance_error(
    tier: str,
    category: str,
    sub_category: str,
    kernel: Kernel,
    kernel_function: str = "",
    kernel_id: str = "",
) -> str | None:
    """None if the entry conforms to the kernel inventory; else a legible reason.

    Id-first. ``kernel_id`` names the exact inventory entry this SLA evidences, and the declared
    (tier, category, sub_category) must equal that entry's slot, which catches a slug that names a
    real function in the wrong part of the tree. ``NON_KERNEL_ID`` conforms by definition and skips
    the slot check.

    ``kernel_function`` is the legacy prose name and is still accepted so that every commit of the
    Plan 9 migration stays green; the slug wins when both are present, and the prose path goes away
    once no manifest carries it.
    """
    if kernel_id:
        if kernel_id == NON_KERNEL_ID:
            return None
        entry = by_id(kernel).get(kernel_id)
        if entry is None:
            return (
                f"kernel_id {kernel_id!r} is not in the kernel inventory "
                f"(registry/_kernel.yaml lists {len(kernel.entries)} ids; "
                f"{NON_KERNEL_ID!r} is reserved for a metric no kernel function covers)"
            )
        if (entry.tier, entry.category, entry.sub_category) != (tier, category, sub_category):
            return (
                f"kernel_id {kernel_id!r} sits in slot "
                f"({entry.tier}, {entry.category}, {entry.sub_category}), "
                f"not ({tier}, {category}, {sub_category})"
            )
        return None
    matches = [
        e
        for e in kernel.entries
        if (e.tier, e.category, e.sub_category) == (tier, category, sub_category)
    ]
    if not matches:
        return f"({tier}, {category}, {sub_category}) is not a catalogued kernel slot"
    if kernel_function:
        if any(e.function == kernel_function for e in matches):
            return None
        elsewhere = next((e for e in kernel.entries if e.function == kernel_function), None)
        if elsewhere is None:
            return f"kernel_function {kernel_function!r} is not in the kernel inventory"
        return (
            f"kernel_function {kernel_function!r} is in slot "
            f"({elsewhere.tier}, {elsewhere.category}, {elsewhere.sub_category}), "
            f"not ({tier}, {category}, {sub_category})"
        )
    if len(matches) > 1:
        names = ", ".join(repr(e.function) for e in matches)
        return (
            f"slot ({tier}, {category}, {sub_category}) maps to {len(matches)} kernel functions; "
            f"set kernel_function to one of: {names}"
        )
    return None
