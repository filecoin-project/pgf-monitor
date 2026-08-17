"""Team-keyed manifest: validate against registry/_schema.json, return typed models."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

from typing import Literal

from fpm.domain import Cadence, ComparisonOperator, Tier, _Model

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "registry" / "_schema.json"

SourceKind = Literal["fixture", "http-json", "onchain-indexsupply"]
ReduceOp = Literal["single", "latest", "avg", "min", "max", "null_ratio"]
ThresholdSource = Literal["signed-appendix", "to-confirm", "provisional"]


DeriveOp = Literal["value", "diff", "age_seconds", "age_days"]
CastOp = Literal["float", "date"]


class ExtractSpec(_Model):
    path: str = "$"
    column: str
    cast: CastOp = "float"
    unit: str = ""
    reduce: ReduceOp = "single"
    timestamp_column: str | None = None
    derive: DeriveOp = "value"
    column2: str | None = None


class TransformSpec(_Model):
    sql: str


class ManifestError(ValueError):
    """Raised when a manifest fails validation."""


class SlaSpec(_Model):
    statement: str
    metric: str
    # None/None means "measured but not scored": the team is monitored, but no threshold has
    # been agreed yet. Several adopted functions are in exactly this state — their agreements
    # are missing, or their signed appendix still marks the number "(to confirm)".
    threshold_op: ComparisonOperator | None = None
    threshold_value: float | None = None
    # Where the number came from. A team passing a bar we invented must not render like a team
    # passing one they signed.
    threshold_source: ThresholdSource = "provisional"
    cadence: Cadence


class SourceSpec(_Model):
    adapter: str
    kind: SourceKind = "fixture"
    endpoint: str = ""
    query: str = ""
    base_url: str = ""
    method: str = "GET"
    params: dict = {}
    paginator: str = "single_page"
    data_selector: str | None = None
    max_table_nesting: int | None = None
    auth_secret_ref: str | None = None
    fixture: str | None = None
    extract: ExtractSpec | None = None


class FunctionSpec(_Model):
    function_id: str
    # lineage of where the entry came from: "oso" = OSO team/reviewer authored;
    # "karma" = harvested from the team's Karma application; "external-pr" = a team or
    # community member submitted it via pull request. Defaults to OSO-authored.
    origin: str = "oso"
    # exact registry/_kernel.yaml function name this SLA evidences. Optional when the
    # (tier, category, sub_category) slot maps to a single kernel function; required (by the
    # kernel conformance check) when the slot is shared by several functions.
    kernel_function: str = ""
    tier: Tier
    category: str = ""
    sub_category: str = ""
    oso_project_slug: str | None = None
    sla: SlaSpec
    source: SourceSpec
    transform: TransformSpec | None = None


class Manifest(_Model):
    team: str
    maintainers: list[str]
    functions: list[FunctionSpec]


def load_manifest(path: str | Path) -> Manifest:
    return manifest_from_raw(yaml.safe_load(Path(path).read_text()))


def manifest_from_raw(raw: object) -> Manifest:
    errors = sorted(
        Draft7Validator(json.loads(_SCHEMA_PATH.read_text())).iter_errors(raw),
        key=lambda e: list(e.path),
    )
    if errors:
        raise ManifestError("; ".join(e.message for e in errors))
    ids = [f["function_id"] for f in raw["functions"]]
    if len(ids) != len(set(ids)):
        raise ManifestError("duplicate function_id in manifest")
    for f in raw["functions"]:
        has_extract = bool(f.get("source", {}).get("extract"))
        has_transform = bool(f.get("transform"))
        if has_extract and has_transform:
            raise ManifestError(
                f"function {f['function_id']} declares both source.extract and transform; choose one"
            )
        if f.get("source", {}).get("kind") == "http-json" and not (has_extract or has_transform):
            raise ManifestError(
                f"function {f['function_id']} (http-json) needs exactly one of source.extract or transform"
            )
    functions = [
        FunctionSpec(
            function_id=f["function_id"],
            origin=f.get("origin", "oso"),
            kernel_function=f.get("kernel_function", ""),
            tier=f["tier"],
            category=f.get("category", ""),
            sub_category=f.get("sub_category", ""),
            oso_project_slug=f.get("oso_project_slug"),
            sla=SlaSpec(
                statement=f["sla"]["statement"],
                metric=f["sla"]["metric"],
                threshold_op=(f["sla"].get("threshold") or {}).get("op"),
                threshold_value=(f["sla"].get("threshold") or {}).get("value"),
                threshold_source=(f["sla"].get("threshold") or {}).get("source", "provisional"),
                cadence=f["sla"]["cadence"],
            ),
            source=SourceSpec(
                adapter=f["source"]["adapter"],
                kind=f["source"].get("kind", "fixture"),
                endpoint=f["source"].get("endpoint", ""),
                query=f["source"].get("query", ""),
                base_url=f["source"].get("base_url", ""),
                method=f["source"].get("method", "GET"),
                params=f["source"].get("params", {}),
                paginator=f["source"].get("paginator", "single_page"),
                data_selector=f["source"].get("data_selector"),
                max_table_nesting=f["source"].get("max_table_nesting"),
                auth_secret_ref=(f["source"].get("auth") or {}).get("secret_ref"),
                fixture=f["source"].get("fixture"),
                extract=(
                    ExtractSpec(**f["source"]["extract"]) if f["source"].get("extract") else None
                ),
            ),
            transform=(TransformSpec(sql=f["transform"]["sql"]) if f.get("transform") else None),
        )
        for f in raw["functions"]
    ]
    return Manifest(team=raw["team"], maintainers=raw["maintainers"], functions=functions)
