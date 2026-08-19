"""The grant bridge: Karma application <-> funded project <-> the files that instrument it.

`registry/_grants.yaml` is the only place that says "this grant is the one funding these metrics".
Before it, three sources each held a fragment and none was authoritative:

* the committee slate in the warehouse (`funding_model_static.decisions`, `csnap-%` events at the
  latest snapshot): app_ref, amount, and an identity-resolved slug that is often a PERSON rather
  than the funded project -- the Curio grant reads "Reiersen" there;
* a `_LABEL` dict inside the dashboard notebook, mapping app_ref to the committee-facing project
  name, which is the only place that correction lived;
* `contracts/<team>.facts.yaml`, one per team, carrying the app_ref and the contract terms.

A project holding two grants (zondax: Core Infra and Beryx; reiers-filecoin: Curio and Plumbline)
could not be expressed by any of them, so "is grant X instrumented?" had no answer. It does now,
and each manifest entry names its payer via `grant_ref` -> `application_ref_id`.

Every field is spelled out rather than inferred, because the old shape conflated three different
questions. `application_*` is what was applied for and where that application lives on Karma;
`funded_project_*` is who is being paid, as named in the signed agreement; `metrics_registry` is
the manifest that instruments the grant. Karma identity is per-APPLICATION, so the slug is mutable
(it follows the application title) while `application_karma_project_id` is the stable key --
cross-batch team identity rides on `funded_project_oso_slug` alone.

Money deliberately does NOT live here. For several grants the committee slate, the signed Exhibit B
and the facts file each carry a different figure, and one grant is part-denominated in FIL. Those
are different claims about different questions, and the facts file -- which is gitignored, because
contract terms are not public -- is where a reconciled figure belongs. A copy here would be one more
number to disagree with.
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
    """Raised when the grant bridge fails schema validation or application_ref_id uniqueness."""


class Grant(_Model):
    #: the funding round this grant belongs to, e.g. "Filecoin ProPGF Batch 3"
    application_funding_round: str
    #: the track. Kernel-only today: a non-kernel grant gets no monitored commitments, so a row
    #: here would imply an instrumentation gap that is not one.
    application_funding_category: str
    #: the Karma application id: the grant's identity everywhere else in the program, and the
    #: target of every manifest entry's `grant_ref`
    application_ref_id: str
    #: the application's own title, verbatim from Karma. Often unlike the funded project's name.
    application_name: str
    #: the Karma project the application is attached to. MUTABLE -- Karma derives it from the
    #: application title, and collisions take a numeric suffix (filponto-1). Empty when the
    #: applicant never linked a profile, which is the case for Curio.
    application_karma_project_slug: str = ""
    #: the Karma project's stable 0x id. Prefer this over the slug as a join key.
    application_karma_project_id: str = ""
    #: committee-facing project name, verbatim from the ProPGF Batch 3 Funded list. The slate's
    #: team_name is often a person; this is the name a reviewer recognises.
    funded_project_name: str
    #: OSO project slug of the party receiving payment, taken from the SIGNED AGREEMENT rather
    #: than from the slate's identity resolution
    funded_project_oso_slug: str
    #: the registry file whose functions[] instrument this grant
    metrics_registry: str
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
    dupes = sorted(
        {
            g.application_ref_id
            for g in grants.grants
            if g.application_ref_id in seen or seen.add(g.application_ref_id)
        }
    )
    if dupes:
        raise GrantError(f"duplicate application_ref_id(s): {', '.join(dupes)}")
    return grants


def by_app_ref(grants: Grants) -> dict[str, Grant]:
    return {g.application_ref_id: g for g in grants.grants}


def by_metrics_registry(grants: Grants) -> dict[str, list[Grant]]:
    """Manifest path -> the grants it instruments. More than one means that file covers two
    grants, so its entries must say which grant funds which metric via `grant_ref`."""
    out: dict[str, list[Grant]] = {}
    for g in grants.grants:
        out.setdefault(g.metrics_registry, []).append(g)
    return out
