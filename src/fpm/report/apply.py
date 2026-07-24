"""Apply the inferred extract to the probed sample via the real derive_observed, to show the value.

Uses the same evaluation path the live adapter uses (fpm.adapters.oso), so the authoring-time
sample the maintainer sees matches what SLA evaluation will actually compute, including `derive`
ops (diff/age_seconds/age_days) and the extract `path` (JSONPath data_selector).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from fpm.manifest import ExtractSpec
from fpm.reduce import derive_observed
from fpm.report.infer import InferenceOutput
from fpm.report.probe import Probe

_SIMPLE_PATH = re.compile(r"^\$\.(\w+)$")


def _descend_path(payload: object, path: str | None) -> object | None:
    """Descend a single-level JSONPath ($, "", None = whole payload; $.<key> = payload[<key>])."""
    if path in ("$", "", None):
        return payload
    m = _SIMPLE_PATH.match(path)
    if m and isinstance(payload, dict) and m.group(1) in payload:
        return payload[m.group(1)]
    return None  # unsupported nested path at authoring time


def observed_value(inference: InferenceOutput, probe: Probe) -> float | None:
    e = inference.extract
    selected = _descend_path(probe.sample_json, e.path)
    if isinstance(selected, dict):
        rows = [selected]
    elif isinstance(selected, list) and all(isinstance(r, dict) for r in selected):
        rows = selected
    else:
        return None
    spec = ExtractSpec(
        path=e.path,
        column=e.column,
        cast=e.cast,
        reduce=e.reduce,
        timestamp_column=e.timestamp_column,
        derive=e.derive,
        column2=e.column2,
    )
    return derive_observed(rows, spec, datetime.now(timezone.utc))
