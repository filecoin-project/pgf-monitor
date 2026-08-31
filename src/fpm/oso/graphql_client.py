"""Live OSO client. Quarantined: never imported by unit tests. Grounded in the Plan 2 spike (see spec).

Endpoint, mutation names, and input shapes were confirmed against api.oso.xyz/v1/graphql.
"""

from __future__ import annotations

from datetime import datetime

import requests
from pyoso import Client

from fpm.oso.client import RunInfo

_TERMINAL = {"SUCCESS", "FAILED", "CANCELED"}


def _dt(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


class GraphqlOsoClient:
    def __init__(self, api_key: str, org_id: str, endpoint: str = "https://api.oso.xyz/v1/graphql"):
        self._endpoint = endpoint
        self._org_id = org_id
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self._sql = Client(api_key=api_key)

    def _gql(self, query: str, variables: dict) -> dict:
        r = requests.post(
            self._endpoint,
            headers=self._headers,
            json={"query": query, "variables": variables},
            timeout=60,
        )
        r.raise_for_status()
        body = r.json()
        if body.get("errors"):
            raise RuntimeError(f"GraphQL errors: {body['errors']}")
        return body["data"]

    def create_dataset(self, org_id: str, name: str, display_name: str) -> str:
        d = self._gql(
            "mutation($i:CreateDatasetInput!){ createDataset(input:$i){ dataset{ id } } }",
            {
                "i": {
                    "orgId": org_id,
                    "name": name,
                    "displayName": display_name,
                    "type": "DATA_INGESTION",
                }
            },
        )
        return d["createDataset"]["dataset"]["id"]

    def _all_datasets(self, node_fields: str) -> list[dict]:
        """Page through the datasets connection (server caps first at 100)."""
        nodes: list[dict] = []
        after: str | None = None
        query = (
            "query($after:String){ datasets(first:100, after:$after){ "
            "pageInfo{ hasNextPage endCursor } edges{ node{ " + node_fields + " } } } }"
        )
        while True:
            conn = self._gql(query, {"after": after})["datasets"]
            nodes.extend(e["node"] for e in conn["edges"])
            if not conn["pageInfo"]["hasNextPage"]:
                return nodes
            after = conn["pageInfo"]["endCursor"]

    def find_dataset(self, org_id: str, name: str) -> str | None:
        for node in self._all_datasets("id name orgId"):
            if node["orgId"] == org_id and node["name"] == name:
                return node["id"]
        return None

    def attach_rest_config(self, dataset_id: str, config: dict) -> str:
        d = self._gql(
            "mutation($i:CreateDataIngestionInput!){ createDataIngestionConfig(input:$i){ id } }",
            {"i": {"rest": {"datasetId": dataset_id, "factoryType": "REST", "config": config}}},
        )
        return d["createDataIngestionConfig"]["id"]

    def get_config(self, dataset_id: str) -> dict | None:
        fields = (
            "id typeDefinition{ __typename ... on DataIngestionDefinition "
            "{ dataIngestion{ config } } }"
        )
        for node in self._all_datasets(fields):
            if node["id"] == dataset_id:
                td = node.get("typeDefinition") or {}
                di = td.get("dataIngestion") or {}
                return di.get("config")
        return None

    def trigger_run(self, dataset_id: str) -> str:
        # OSO changed this mutation's payload on 2026-08-22: `createDataIngestionRunRequest` now
        # returns CreateRunGroupPayload (a run GROUP wrapping one run per selected model) and no
        # longer has a `run` field, so the old selection failed GraphQL validation with a bare
        # 400 -- every metric raised, every reading landed indeterminate, and the workflow still
        # reported success. The group carries its runs inline and already attached (QUEUED) in
        # the mutation response, so one round trip still yields the run id.
        # `createStaticModelRunRequest` followed on 2026-08-27 and now returns the same payload;
        # see fpm/oso/static_model.py. Assume any remaining run-request mutation is next.
        d = self._gql(
            "mutation($i:CreateDataIngestionRunRequestInput!){ "
            "createDataIngestionRunRequest(input:$i){ success message "
            "runGroup{ id runs{ edges{ node{ id } } } } } }",
            {"i": {"datasetId": dataset_id}},
        )
        payload = d["createDataIngestionRunRequest"]
        group = payload.get("runGroup") or {}
        edges = ((group.get("runs") or {}).get("edges")) or []
        if not edges:
            raise RuntimeError(
                f"createDataIngestionRunRequest returned no run for dataset {dataset_id} "
                f"(runGroup={group.get('id')!r}, success={payload.get('success')!r}, "
                f"message={payload.get('message')!r})"
            )
        return edges[0]["node"]["id"]

    def get_runs(self, dataset_id: str) -> list[RunInfo]:
        d = self._gql(
            "query($n:Int!){ runs(first:$n){ edges{ node{ "
            "id status datasetId startedAt finishedAt logsUrl } } } }",
            {"n": 50},
        )
        out = []
        for e in d["runs"]["edges"]:
            n = e["node"]
            if n["datasetId"] == dataset_id:
                out.append(
                    RunInfo(
                        run_id=n["id"],
                        status=n["status"],
                        started_at=_dt(n.get("startedAt")),
                        finished_at=_dt(n.get("finishedAt")),
                        logs_url=n.get("logsUrl"),
                    )
                )
        return out

    def table_full_name(self, dataset_id: str) -> str | None:
        for node in self._all_datasets("id tables{ edges{ node{ fullName } } }"):
            if node["id"] == dataset_id:
                tables = node["tables"]["edges"]
                return tables[0]["node"]["fullName"] if tables else None
        return None

    def query(self, sql: str) -> list[dict]:
        return self._sql.to_pandas(sql).to_dict("records")

    def delete_dataset(self, dataset_id: str) -> None:
        self._gql("mutation($id:ID!){ deleteDataset(id:$id){ success } }", {"id": dataset_id})
