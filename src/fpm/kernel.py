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


def conformance_error(
    tier: str,
    category: str,
    sub_category: str,
    kernel: Kernel,
    kernel_function: str = "",
) -> str | None:
    """None if the entry conforms to the kernel inventory; else a legible reason.

    Conformance means: (tier, category, sub_category) is a catalogued slot, and the specific
    kernel function is identifiable. When a slot is shared by several functions, ``kernel_function``
    (the exact inventory name) is required to say which one; when it names a function, that function
    must actually live in the declared slot.
    """
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
