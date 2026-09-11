"""Team-keyed manifest: validate against registry/_schema.json, return typed models."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

from typing import Literal

from fpm.domain import Cadence, ComparisonOperator, Tier, _Model

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "registry" / "_schema.json"

SourceKind = Literal["fixture", "http-json", "oso-sql", "onchain-indexsupply"]
ReduceOp = Literal["single", "latest", "avg", "min", "max", "null_ratio"]
ThresholdSource = Literal["signed-appendix", "to-confirm", "provisional"]
# Why a function carries no threshold. Absent bars used to be explained in long YAML comments,
# which put quoted contract terms into a public repo and made the manifests unreadable. The
# reason is data: one of these values, with the narrative kept in the maintainer-local facts file.
#   no-agreement     no signed agreement has been located for this grant at all
#   no-signed-bar    the appendix names the metric but agrees no number (often "(to confirm)")
#   not-in-appendix  an agreement exists, but this metric does not appear in its s3
#   doc-conflict     the appendix states a bar that contradicts itself
#   out-of-scope     the agreement explicitly places the measured thing outside the grant
#   contract-not-executed
#                    the appendix DOES state a number, but the agreement carrying it is not
#                    executed, so nobody has yet promised it. Distinct from no-signed-bar, which
#                    means no number was ever agreed: this bar exists on paper and is not yet
#                    binding, so the number stays recorded in the facts file and the metric
#                    renders measured-but-unscored until the contract is countersigned.
UnscoredReason = Literal[
    "no-agreement",
    "no-signed-bar",
    "not-in-appendix",
    "doc-conflict",
    "out-of-scope",
    "contract-not-executed",
]


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
    # Set only when threshold_value is None; manifest_from_raw rejects a function that states
    # both, since a scored bar and a reason for having none contradict each other.
    unscored_reason: UnscoredReason | None = None
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
    # kind `oso-sql` only: one SELECT over warehouse tables that are already on
    # registry/_sql_allowlist.txt. Not a transform — a transform binds the single `raw` table its
    # own ingestion landed, whereas this reads tables OSO already holds and so can join them.
    # Kept as its own field rather than reusing `transform.sql` so a reviewer can see at a glance
    # which validation regime applies; the two are checked against different table rules.
    sql: str = ""


class FunctionSpec(_Model):
    function_id: str
    # lineage of where the entry came from: "oso" = OSO team/reviewer authored;
    # "karma" = harvested from the team's Karma application; "external-pr" = a team or
    # community member submitted it via pull request. Defaults to OSO-authored.
    origin: str = "oso"
    # slug of the registry/_kernel.yaml entry this SLA evidences. Required by the schema; the
    # model defaults to "" so directly-constructed specs in tests stay valid. "non-kernel" says
    # the metric measures something the kernel inventory does not name.
    kernel_id: str = ""
    tier: Tier
    category: str = ""
    sub_category: str = ""
    # OSO project slug of the party RECEIVING PAYMENT for this work. Not the code's project and
    # not the team's org: those are different things, and one field used to carry all three.
    funded_project_oso_slug: str = ""
    # `application_ref_id` of the grant in registry/_grants.yaml that PAYS for this metric.
    # funded_project_oso_slug names the payee, which is not enough when one payee holds two
    # grants: both zondax.yaml entries read slug `zondax` yet only one of Core Infra and Beryx
    # funds each. Empty is legal for an entry no grant pays for (the filfox cross-check, whose
    # slug is `unfunded`) and for drafts staged before an award.
    grant_ref: str = ""
    # GitHub repositories the funded work covers, as lowercase owner/name -- OSO's GITHUB_REPO
    # artifact identity, so the list joins straight to artifacts_by_project. Empty is honest for
    # work measured through an RPC endpoint, an explorer or a status page.
    repos: list[str] = []
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
        # Coherence before kind-specific rules, so a mismatch reports itself rather than whatever
        # the mis-declared kind happens to complain about first.
        #
        # The static gates branch on `source.kind`; `measure` dispatches on `source.adapter`.
        # Left free to disagree, a function can declare kind http-json -- so validate_pr checks a
        # host, an ingestion config and an extract, and dry_run_pr measures it through OsoAdapter
        # and reports PASS -- while the nightly dispatches to OsoSqlAdapter and runs source.sql
        # instead. The committee would approve and live-prove a derivation that never executes.
        _kind = f.get("source", {}).get("kind", "fixture")
        _adapter = f.get("source", {}).get("adapter", "")
        if (_kind == "oso-sql") != (_adapter == "oso-sql"):
            raise ManifestError(
                f"function {f['function_id']} has source.kind {_kind!r} with source.adapter "
                f"{_adapter!r}; `oso-sql` must be both or neither, because the PR gates read the "
                "kind and the runtime reads the adapter"
            )
        has_extract = bool(f.get("source", {}).get("extract"))
        has_transform = bool(f.get("transform"))
        if has_extract and has_transform:
            raise ManifestError(
                f"function {f['function_id']} declares both source.extract and transform; choose one"
            )
        if f["sla"].get("threshold") and f["sla"].get("unscored_reason"):
            raise ManifestError(
                f"function {f['function_id']} states a threshold and an unscored_reason; "
                "a scored bar has no reason for being unscored"
            )
        if _kind == "http-json" and not (has_extract or has_transform):
            raise ManifestError(
                f"function {f['function_id']} (http-json) needs exactly one of source.extract or transform"
            )
        if _kind == "oso-sql":
            # The warehouse path derives its value from source.sql alone. Accepting an extract or
            # a transform beside it would leave two candidate derivations in one entry, and the
            # reader could not tell which one produced the number.
            if not (f["source"].get("sql") or "").strip():
                raise ManifestError(f"function {f['function_id']} (oso-sql) needs source.sql")
            if has_extract or has_transform:
                raise ManifestError(
                    f"function {f['function_id']} (oso-sql) must not also declare "
                    "source.extract or transform; source.sql is the whole derivation"
                )
            # Nothing is fetched, so a fetch declaration here would misrepresent the metric to a
            # reviewer -- and base_url is what the egress host allowlist is checked against.
            fetchy = sorted(
                k for k in ("base_url", "endpoint", "query", "params") if f["source"].get(k)
            )
            if fetchy:
                raise ManifestError(
                    f"function {f['function_id']} (oso-sql) performs no HTTP fetch; remove "
                    f"{fetchy} from source"
                )
    functions = [
        FunctionSpec(
            function_id=f["function_id"],
            origin=f.get("origin", "oso"),
            kernel_id=f.get("kernel_id", ""),
            tier=f["tier"],
            category=f.get("category", ""),
            sub_category=f.get("sub_category", ""),
            funded_project_oso_slug=f.get("funded_project_oso_slug", ""),
            grant_ref=f.get("grant_ref", ""),
            repos=list(f.get("repos") or []),
            sla=SlaSpec(
                statement=f["sla"]["statement"],
                metric=f["sla"]["metric"],
                threshold_op=(f["sla"].get("threshold") or {}).get("op"),
                threshold_value=(f["sla"].get("threshold") or {}).get("value"),
                threshold_source=(f["sla"].get("threshold") or {}).get("source", "provisional"),
                unscored_reason=f["sla"].get("unscored_reason"),
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
                sql=f["source"].get("sql", ""),
            ),
            transform=(TransformSpec(sql=f["transform"]["sql"]) if f.get("transform") else None),
        )
        for f in raw["functions"]
    ]
    return Manifest(team=raw["team"], maintainers=raw["maintainers"], functions=functions)
