"""Guard: manifest_from_raw enumerates fields by hand, so a new model field is silently dropped.

`FIELD_BUCKETS` sits a layer above and cannot see this -- it classifies fields for the goalpost
diff, but a field the loader never reads is absent from every Manifest and so never diffs. This
test parses one raw manifest in which EVERY field is set to a non-default value, then asserts both
directions: each field arrives with the value the YAML gave it, and the case table covers exactly
the fields the models declare (so adding a field fails here until it is mapped and covered).
"""

from fpm.manifest import (
    ExtractSpec,
    FunctionSpec,
    Manifest,
    SlaSpec,
    SourceSpec,
    TransformSpec,
    manifest_from_raw,
)

# Function 0 is http-json with an extract; function 1 is a fixture with a transform. Two are
# needed because a function may declare source.extract or transform but never both, and because
# a scored threshold and an unscored_reason describe mutually exclusive states.
_RAW = {
    "team": "acme",
    "maintainers": ["acme-bot", "acme-ops"],
    "functions": [
        {
            "function_id": "acme-http",
            "origin": "external-pr",
            "kernel_id": "chain-sync-state",
            "tier": "irreplaceable",
            "category": "UX/DX",
            "sub_category": "Tooling",
            "funded_project_oso_slug": "drand",
            "grant_ref": "APP-ACME-001",
            "repos": ["acme/widget"],
            "sla": {
                "statement": "the endpoint stays fresh",
                "metric": "head_lag_epochs",
                "threshold": {"op": "<=", "value": 3.0, "source": "signed-appendix"},
                "cadence": "weekly",
            },
            "source": {
                "adapter": "rest",
                "kind": "http-json",
                "endpoint": "status",
                "query": "status",
                "base_url": "https://api.example.com/",
                "method": "POST",
                "params": {"limit": 5},
                "paginator": "json_link",
                "data_selector": "items",
                "max_table_nesting": 2,
                "auth": {"secret_ref": "ACME_API_TOKEN"},
                "extract": {
                    "path": "$.items",
                    "column": "lag",
                    "cast": "date",
                    "unit": "epochs",
                    "reduce": "latest",
                    "timestamp_column": "observed_at",
                    "derive": "diff",
                    "column2": "lag_prev",
                },
            },
        },
        {
            "function_id": "acme-fixture",
            "kernel_id": "chain-sync-state",
            "tier": "essential",
            "category": "UX/DX",
            "sub_category": "Tooling",
            "funded_project_oso_slug": "drand",
            "sla": {
                "statement": "commits keep landing",
                "metric": "commit_age_days",
                "unscored_reason": "no-agreement",
                "cadence": "monthly",
            },
            "source": {"adapter": "fixture", "fixture": "acme.json"},
            "transform": {"sql": "SELECT max(lag) FROM raw"},
        },
    ],
}

# model -> {field: (function index it is set on, value the YAML above gives it)}. Every value is
# deliberately different from the model default, so a field the loader forgets to map fails.
_CASES = {
    Manifest: {
        "team": (None, "acme"),
        "maintainers": (None, ["acme-bot", "acme-ops"]),
        "functions": (None, 2),  # length, not identity
    },
    FunctionSpec: {
        "function_id": (0, "acme-http"),
        "origin": (0, "external-pr"),
        "kernel_id": (0, "chain-sync-state"),
        "tier": (0, "irreplaceable"),
        "category": (0, "UX/DX"),
        "sub_category": (0, "Tooling"),
        "funded_project_oso_slug": (0, "drand"),
        "grant_ref": (0, "APP-ACME-001"),
        "repos": (0, ["acme/widget"]),
        "sla": (0, SlaSpec),
        "source": (0, SourceSpec),
        "transform": (1, TransformSpec),
    },
    SlaSpec: {
        "statement": (0, "the endpoint stays fresh"),
        "metric": (0, "head_lag_epochs"),
        "threshold_op": (0, "<="),
        "threshold_value": (0, 3.0),
        "threshold_source": (0, "signed-appendix"),
        "cadence": (0, "weekly"),
        "unscored_reason": (1, "no-agreement"),
    },
    SourceSpec: {
        "adapter": (0, "rest"),
        "kind": (0, "http-json"),
        "endpoint": (0, "status"),
        "query": (0, "status"),
        "base_url": (0, "https://api.example.com/"),
        "method": (0, "POST"),
        "params": (0, {"limit": 5}),
        "paginator": (0, "json_link"),
        "data_selector": (0, "items"),
        "max_table_nesting": (0, 2),
        "auth_secret_ref": (0, "ACME_API_TOKEN"),
        "fixture": (1, "acme.json"),
        "extract": (0, ExtractSpec),
    },
    ExtractSpec: {
        "path": (0, "$.items"),
        "column": (0, "lag"),
        "cast": (0, "date"),
        "unit": (0, "epochs"),
        "reduce": (0, "latest"),
        "timestamp_column": (0, "observed_at"),
        "derive": (0, "diff"),
        "column2": (0, "lag_prev"),
    },
    TransformSpec: {"sql": (1, "SELECT max(lag) FROM raw")},
}


def _holder(model, manifest, index):
    """The object of type `model` that function `index` of the parsed manifest carries."""
    if model is Manifest:
        return manifest
    fn = manifest.functions[index]
    return {
        FunctionSpec: lambda: fn,
        SlaSpec: lambda: fn.sla,
        SourceSpec: lambda: fn.source,
        ExtractSpec: lambda: fn.source.extract,
        TransformSpec: lambda: fn.transform,
    }[model]()


def test_every_declared_field_is_covered_by_this_test():
    for model, cases in _CASES.items():
        assert set(cases) == set(model.model_fields), (
            f"{model.__name__} fields not covered here: "
            f"{set(model.model_fields) ^ set(cases)} -- add the field to _RAW and _CASES, and "
            f"map it in manifest_from_raw"
        )


def test_manifest_from_raw_carries_every_field():
    manifest = manifest_from_raw(_RAW)
    for model, cases in _CASES.items():
        for field, (index, expected) in cases.items():
            actual = getattr(_holder(model, manifest, index), field)
            if field == "functions":
                assert len(actual) == expected
            elif isinstance(expected, type):
                assert isinstance(actual, expected), f"{model.__name__}.{field} was dropped"
            else:
                assert actual == expected, f"{model.__name__}.{field} was dropped"
