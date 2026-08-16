"""Live OSO Static Model client. Quarantined: never imported by unit tests.

Mirrors GraphqlOsoClient (see graphql_client.py): same `_gql` POST-with-bearer-auth helper, same
bounded-poll pattern for run requests. Mutation names, input shapes, and response field accessors
are confirmed against the live api.oso.xyz endpoint via scripts/live_land_smoke.py.
"""

from __future__ import annotations

import time

import requests
from pyoso import Client

from fpm.oso.client import RunInfo

_TERMINAL = {"SUCCESS", "FAILED", "CANCELED"}


class GraphqlStaticModelClient:
    """Implements the `StaticModelClient` protocol (fpm.land) against api.oso.xyz/v1/graphql."""

    def __init__(
        self,
        api_key: str,
        org_id: str,
        endpoint: str = "https://api.oso.xyz/v1/graphql",
        poll_attempts: int = 30,
        poll_sleep: float = 10.0,
    ) -> None:
        self._endpoint = endpoint
        self._org_id = org_id
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self._sql = Client(api_key=api_key)
        self._poll_attempts = poll_attempts
        self._poll_sleep = poll_sleep

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

    def ensure_static_dataset(self, org_id: str, name: str) -> str:
        for node in self._all_datasets("id name orgId"):
            if node["orgId"] == org_id and node["name"] == name:
                return node["id"]
        d = self._gql(
            "mutation($i:CreateDatasetInput!){ createDataset(input:$i){ dataset{ id } } }",
            {
                "i": {
                    "orgId": org_id,
                    "name": name,
                    "displayName": name,
                    "type": "STATIC_MODEL",
                }
            },
        )
        # ASSUMPTION (mirrors GraphqlOsoClient.create_dataset): response is
        # createDataset.dataset.id. Confirmed live.
        return d["createDataset"]["dataset"]["id"]

    def ensure_static_model(self, org_id: str, dataset_id: str, name: str) -> str:
        """Reuse the static model if it already exists, else create it.

        Must be idempotent, exactly like ensure_static_dataset: `land` republishes the SAME
        two tables on every review, so an unconditional createStaticModel fails with
        ALREADY_EXISTS on the second land and no verdict can ever be published twice.

        The staticModels connection exposes `dataset { id }`, not a flat datasetId, and the
        `where` filter keys on DATABASE COLUMN names (name, org_id, dataset_id).
        """
        d = self._gql(
            "query($w:JSON){ staticModels(first:50, where:$w){ edges{ node{ "
            "id name orgId dataset{ id } } } } }",
            {"w": {"name": {"eq": name}, "dataset_id": {"eq": dataset_id}}},
        )
        for edge in d["staticModels"]["edges"]:
            node = edge["node"]
            if node["orgId"] == org_id and node["dataset"]["id"] == dataset_id:
                return node["id"]
        d = self._gql(
            "mutation($i:CreateStaticModelInput!){ createStaticModel(input:$i){ "
            "staticModel{ id } } }",
            {"i": {"orgId": org_id, "datasetId": dataset_id, "name": name}},
        )
        # ASSUMPTION: response is createStaticModel.staticModel.id (mirrors the
        # createDataset -> dataset{id} shape). Confirmed live.
        return d["createStaticModel"]["staticModel"]["id"]

    def upload_csv(self, static_model_id: str, csv_text: str) -> None:
        # createStaticModelUploadUrl takes staticModelId directly (not an Input wrapper) and
        # returns the pre-signed URL as a scalar String (no subselection). Confirmed live.
        d = self._gql(
            "mutation($id:ID!){ createStaticModelUploadUrl(staticModelId:$id) }",
            {"id": static_model_id},
        )
        url = d["createStaticModelUploadUrl"]
        # The pre-signed URL is S3-style (Cloudflare R2) and accepts PUT. Confirmed live.
        r = requests.put(url, data=csv_text.encode("utf-8"), timeout=60)
        r.raise_for_status()

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
                out.append(RunInfo(run_id=n["id"], status=n["status"], logs_url=n.get("logsUrl")))
        return out

    def run_static_model(self, dataset_id: str) -> None:
        d = self._gql(
            "mutation($i:CreateStaticModelRunRequestInput!){ "
            "createStaticModelRunRequest(input:$i){ run{ id } } }",
            {"i": {"datasetId": dataset_id}},
        )
        # ASSUMPTION: response is createStaticModelRunRequest.run.id (mirrors
        # createDataIngestionRunRequest.run.id). Confirmed live.
        run_id = d["createStaticModelRunRequest"]["run"]["id"]
        for attempt in range(self._poll_attempts):
            try:
                runs = {r.run_id: r for r in self.get_runs(dataset_id)}
                run = runs.get(run_id)
                if run and run.status in _TERMINAL:
                    return
            except Exception:
                pass  # transient; retry on the next attempt
            if self._poll_sleep and attempt < self._poll_attempts - 1:
                time.sleep(self._poll_sleep)

    def grant_public(self, static_model_id: str) -> None:
        # Public = READ with no target user/org. GrantResourcePermissionInput has no "targets"
        # field; omitting targetUserId/targetOrgId is what makes the grant public. Confirmed
        # live (returns {success: true}).
        self._gql(
            "mutation($i:GrantResourcePermissionInput!){ "
            "grantResourcePermission(input:$i){ success } }",
            {
                "i": {
                    "id": static_model_id,
                    "resourceType": "STATIC_MODEL",
                    "permissionLevel": "READ",
                }
            },
        )

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
