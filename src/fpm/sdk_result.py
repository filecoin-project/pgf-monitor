"""Extract a structured payload from an SDK result, tolerant of SDK/backend variance.

Prefer ResultMessage.structured_output; fall back to parsing ResultMessage.result as JSON.
Some SDK/backend paths (observed: claude-agent-sdk 0.2.116 on the Vertex path) return the
requested JSON in result text rather than populating structured_output.
"""

from __future__ import annotations

import json


def structured_payload(structured_output: dict | None, result_text: str | None) -> dict:
    """Return the model's JSON object from structured_output, else parsed from result_text."""
    if structured_output:
        return structured_output
    if result_text:
        text = result_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")[1:]  # drop the opening ``` or ```json line
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])
            raise
    raise RuntimeError("model returned neither structured_output nor result text")
