"""The grant bridge: Karma application id <-> OSO project slug <-> the files that instrument it.

`registry/_grants.yaml` is the only place that says "this grant is the one funding these metrics".
Before it, three sources each held a fragment and none was authoritative:

* the committee slate in the warehouse (`funding_model_static.decisions`, `csnap-%` events at the
  latest snapshot): app_ref, amount, and an identity-resolved slug that is often a PERSON rather
  than the funded project -- the Curio grant reads "Reiersen" there;
* a `_LABEL` dict inside the dashboard notebook, mapping app_ref to the committee-facing project
  name, which is the only place that correction lived;
* `contracts/<team>.facts.yaml`, one per team, carrying the app_ref and the contract terms.

A project holding two grants (zondax: Core Infra and Beryx; reiers-filecoin: Curio and Plumbline)
could not be expressed by any of them, so "is grant X instrumented?" had no answer. It does now.

Money deliberately does NOT live here. The same grant reads $300,000 on the slate, $320,000 plus
67,200 FIL in its signed Exhibit B, and 213,332 in its facts file (the through-December tranches).
Those are three different claims and the facts file is where a reconciled figure belongs; a fourth
copy here would just be a fourth number to disagree with.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

from fpm.domain import _Model

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "registry" / "_grants_schema.json"
_GRANTS_PATH = Path(__file__).resolve().parents[2] / "registry" / "_grants.yaml"


class GrantError(ValueError):
    """Raised when the grant bridge fails schema validation or app_ref uniqueness."""


class Grant(_Model):
    #: the Karma application id: the grant's identity everywhere else in the program
    app_ref: str
    #: committee-facing project name. The slate's team_name is often a person; this is the label
    #: a reviewer recognises.
    label: str
    #: OSO project slug of the party receiving payment, taken from the signed agreement. Empty
    #: only when nobody is being paid: Pyth sits on the slate with no amount and no OSO project.
    funded_project_oso_slug: str = ""
    status: str
    #: the registry file whose metrics instrument this grant. Empty means not instrumented yet,
    #: which is the gap list.
    manifest: str = ""
    #: the contract facts used to render the grant agreement appendix
    facts: str = ""
    #: Drive file id of the signed agreement, so a reviewer can get to the source
    agreement_doc_id: str = ""
    note: str = ""


class Grants(_Model):
    grants: list[Grant]


def load_grants(path: str | Path = _GRANTS_PATH) -> Grants:
    raw = yaml.safe_load(Path(path).read_text())
    errors = sorted(
        Draft7Validator(json.loads(_SCHEMA_PATH.read_text())).iter_errors(raw),
        key=lambda e: list(e.path),
    )
    if errors:
        raise GrantError("; ".join(e.message for e in errors))
    grants = Grants(grants=[Grant(**g) for g in raw["grants"]])
    seen: set[str] = set()
    dupes = sorted({g.app_ref for g in grants.grants if g.app_ref in seen or seen.add(g.app_ref)})
    if dupes:
        raise GrantError(f"duplicate app_ref(s): {', '.join(dupes)}")
    # A funded grant pays someone, so it must name them. An unresolved or unfunded row need not:
    # Pyth sits on the slate with no amount and no OSO project, and forcing a slug there would be
    # inventing a payee.
    unpaid = [
        g.app_ref for g in grants.grants if g.status == "funded" and not g.funded_project_oso_slug
    ]
    if unpaid:
        raise GrantError(f"funded grant(s) with no funded_project_oso_slug: {', '.join(unpaid)}")
    return grants


def by_app_ref(grants: Grants) -> dict[str, Grant]:
    return {g.app_ref: g for g in grants.grants}


def by_manifest(grants: Grants) -> dict[str, list[Grant]]:
    """Manifest path -> the grants it instruments. More than one means that file covers two
    grants, which is legal but means its entries must say which grant funds which metric."""
    out: dict[str, list[Grant]] = {}
    for g in grants.grants:
        if g.manifest:
            out.setdefault(g.manifest, []).append(g)
    return out
