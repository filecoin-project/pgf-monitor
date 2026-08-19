"""Draft manifests: registry/drafts/*.yaml with an `x_draft` annotation block.

A draft is a normal team manifest plus one extra top-level key, `x_draft`, carrying
slate/provenance annotations that the strict registry schema (additionalProperties:
false) deliberately rejects. Promotion = strip `x_draft`, satisfy the same checks the
PR gate runs, and move the file into registry/ proper. The strip is textual so the
probe-evidence and threshold-rationale comments survive.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from fpm.governance.allowlist import host_allowed, host_of
from fpm.kernel import Kernel, conformance_error
from fpm.manifest import Manifest, manifest_from_raw
from fpm.transform.validate import TransformSqlError, validate_transform_sql


def split_draft(path: str | Path) -> tuple[Manifest, dict]:
    """Load a draft file: strip x_draft, validate the rest as a normal manifest."""
    raw = yaml.safe_load(Path(path).read_text())
    x_draft = raw.pop("x_draft", {}) if isinstance(raw, dict) else {}
    return manifest_from_raw(raw), x_draft or {}


def promotion_problems(manifest: Manifest, kernel: Kernel, allowlist: set[str]) -> list[str]:
    """Everything the PR gate would reject, in one list. Empty = promotable as-is."""
    problems: list[str] = []
    for fn in manifest.functions:
        err = conformance_error(fn.tier, fn.category, fn.sub_category, kernel, fn.kernel_id)
        if err is not None:
            problems.append(f"{fn.function_id}: {err}")
        if fn.transform is not None:
            try:
                validate_transform_sql(fn.transform.sql)
            except TransformSqlError as exc:
                problems.append(f"{fn.function_id}: transform SQL rejected ({exc})")
        if fn.source.kind == "fixture":
            continue
        if not host_allowed(fn.source.base_url, allowlist):
            problems.append(
                f"{fn.function_id}: host not on allowlist ({host_of(fn.source.base_url)})"
            )
    return problems


def strip_x_draft_text(text: str, comment: bool = False) -> str:
    """Remove the top-level x_draft block textually, preserving all other lines/comments.

    With comment=True the block is commented out instead of dropped — promotion keeps
    the slate context and unmeasured-function rationale visible in the adopted file.
    """
    out: list[str] = []
    in_block = False
    for line in text.splitlines(keepends=True):
        if line.startswith("x_draft:"):
            in_block = True
            if comment:
                out.append("# x_draft (promotion note — annotations preserved as comments):\n")
            continue
        if in_block:
            # block continues while lines are indented or blank
            if line.strip() == "" or line.startswith((" ", "\t")):
                if comment and line.strip():
                    out.append("# " + line)
                continue
            in_block = False
        out.append(line)
    return "".join(out)
