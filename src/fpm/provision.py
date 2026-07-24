"""Translate a manifest source into an OSO REST ingestion config, and gate egress for integrity.

The egress gate is an integrity control (we provision exactly the reviewed endpoint), NOT SSRF
safety: OSO workers do the fetching and have no egress guard, so a malicious declared endpoint is
not mitigable here. Safety rests on committee PR review plus an independent host allowlist.
"""

from __future__ import annotations

from urllib.parse import urlparse

from fpm.domain import MeasurementWindow
from fpm.hashing import canonical_json, sha256_hex
from fpm.manifest import FunctionSpec


class EgressError(ValueError):
    """Raised when a declared source host is not on the provisioning allowlist."""


def _strip_secrets(obj: object) -> object:
    """Replace any {$type: secret, ...} subtree with a sentinel so fingerprints ignore how a
    secret is represented (our build carries the ref value; OSO stores a name marker)."""
    if isinstance(obj, dict):
        if obj.get("$type") == "secret":
            return {"$type": "secret"}
        return {k: _strip_secrets(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_secrets(x) for x in obj]
    return obj


def config_shape_fingerprint(config: dict) -> str:
    """Hash a config's structural shape, ignoring secret representation. Used to detect whether an
    existing durable dataset's attached config still matches the current manifest declaration."""
    return sha256_hex(canonical_json(_strip_secrets(config)))


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text.lower())


def dataset_name(team: str, function_id: str) -> str:
    return f"fpm_{_slug(team)}_{_slug(function_id)}"


def resource_name(team: str, function_id: str) -> str:
    return f"fpm_{_slug(team)}_{_slug(function_id)}_t"


def _auth_block(fn: FunctionSpec) -> dict | None:
    if not fn.source.auth_secret_ref:
        return None
    return {"type": "bearer", "token": {"$type": "secret", "value": fn.source.auth_secret_ref}}


def build_ingestion_config(fn: FunctionSpec, window: MeasurementWindow, team: str) -> dict:
    endpoint: dict = {
        "config_type": "advanced",
        "path": fn.source.query,
        "method": fn.source.method,
    }
    if fn.source.params:
        # dlt rest_api semantics: `params` = URL query params; a POST payload
        # (JSON-RPC, GraphQL) must ride in `json` or it arrives as ?k=v -> 4xx.
        endpoint["json" if fn.source.method == "POST" else "params"] = fn.source.params
    if fn.source.data_selector:
        endpoint["data_selector"] = fn.source.data_selector
    elif fn.source.extract and fn.source.extract.path not in ("", "$"):
        endpoint["data_selector"] = fn.source.extract.path
    client: dict = {"base_url": fn.source.base_url}
    auth = _auth_block(fn)
    if auth:
        client["auth"] = auth
    resource: dict = {
        "name": resource_name(team, fn.function_id),
        "endpoint": endpoint,
        "write_disposition": "replace",
    }
    if fn.source.max_table_nesting is not None:
        resource["max_table_nesting"] = fn.source.max_table_nesting
    return {"client": client, "resources": [resource]}


def config_fingerprint(fn: FunctionSpec, window: MeasurementWindow) -> dict:
    return {
        "base_url": fn.source.base_url,
        "query": fn.source.query,
        "method": fn.source.method,
        "params": fn.source.params,
        "paginator": fn.source.paginator,
        "kind": fn.source.kind,
        "window_start": window.start.isoformat(),
        "window_end": window.end.isoformat(),
    }


def assert_egress_allowed(fn: FunctionSpec, allowlist: set[str]) -> None:
    host = urlparse(fn.source.base_url).hostname or ""
    if host not in allowlist:
        raise EgressError(f"host {host!r} is not on the provisioning allowlist")
