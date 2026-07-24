"""Render a goalpost classification as Markdown for the CI job summary."""

from __future__ import annotations

from fpm.governance.classify import ClassifiedChange, has_material


def _row(i: ClassifiedChange) -> str:
    where = i.function_id or "(manifest)"
    detail = i.reason
    if i.kind == "modified":
        return f"- `{where}` `{i.field_path}` {i.old!r} -> {i.new!r} ({detail})"
    return f"- `{where}` {i.field_path} {i.kind} ({detail})"


def render_report(items: list[ClassifiedChange]) -> str:
    if not items:
        return "### Goalpost check\n\nNo changes to committed manifests."
    lines = ["### Goalpost check", ""]
    if has_material(items):
        lines.append("**Material changes present. Committee review required.**")
    else:
        lines.append("No material changes (new/trivial only).")
    for bucket in ("material", "new", "trivial"):
        rows = [i for i in items if i.bucket == bucket]
        if rows:
            lines += ["", f"**{bucket.upper()}**", *[_row(r) for r in rows]]
    return "\n".join(lines)
