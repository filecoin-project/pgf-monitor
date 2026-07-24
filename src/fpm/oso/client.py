"""OsoIngestionClient: the seam between our pipeline and OSO's ingestion + SQL surfaces."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from fpm.domain import _Model


class RunInfo(_Model):
    run_id: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    dlt_load_id: str | None = None
    logs_url: str | None = None


@runtime_checkable
class OsoIngestionClient(Protocol):
    def create_dataset(self, org_id: str, name: str, display_name: str) -> str: ...
    def find_dataset(self, org_id: str, name: str) -> str | None: ...
    def attach_rest_config(self, dataset_id: str, config: dict) -> str: ...
    def get_config(self, dataset_id: str) -> dict | None: ...
    def trigger_run(self, dataset_id: str) -> str: ...
    def get_runs(self, dataset_id: str) -> list[RunInfo]: ...
    def table_full_name(self, dataset_id: str) -> str | None: ...
    def query(self, sql: str) -> list[dict]: ...
    def delete_dataset(self, dataset_id: str) -> None: ...


class FakeOsoClient:
    """Deterministic in-memory client for offline tests. No network."""

    def __init__(
        self,
        rows_by_dataset: dict | None = None,
        run_status: str = "SUCCESS",
        query_rows: list[dict] | None = None,
    ) -> None:
        self._run_status = run_status
        self._query_rows = query_rows if query_rows is not None else []
        self._rows_by_dataset = rows_by_dataset or {}
        self._datasets: dict[str, dict] = {}  # id -> {org, name}
        self._runs: dict[str, list[RunInfo]] = {}
        self._configs: dict[str, dict] = {}  # id -> attached config
        self._counter = 0

    def _next(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}-{self._counter}"

    def create_dataset(self, org_id: str, name: str, display_name: str) -> str:
        ds = self._next("ds")
        self._datasets[ds] = {"org": org_id, "name": name}
        self._runs[ds] = []
        return ds

    def find_dataset(self, org_id: str, name: str) -> str | None:
        for ds, meta in self._datasets.items():
            if meta["org"] == org_id and meta["name"] == name:
                return ds
        return None

    def attach_rest_config(self, dataset_id: str, config: dict) -> str:
        self._configs[dataset_id] = config
        return self._next("ing")

    def get_config(self, dataset_id: str) -> dict | None:
        return self._configs.get(dataset_id)

    def trigger_run(self, dataset_id: str) -> str:
        run_id = self._next("run")
        now = datetime(2026, 7, 1, tzinfo=timezone.utc)
        self._runs.setdefault(dataset_id, []).append(
            RunInfo(
                run_id=run_id,
                status=self._run_status,
                started_at=now,
                finished_at=now,
                dlt_load_id="fake-load",
                logs_url="fake://logs",
            )
        )
        return run_id

    def get_runs(self, dataset_id: str) -> list[RunInfo]:
        return list(self._runs.get(dataset_id, []))

    def table_full_name(self, dataset_id: str) -> str | None:
        meta = self._datasets.get(dataset_id)
        return f"filecoin.{meta['name']}.{meta['name']}_t" if meta else None

    def query(self, sql: str) -> list[dict]:
        return list(self._query_rows)

    def delete_dataset(self, dataset_id: str) -> None:
        self._datasets.pop(dataset_id, None)
        self._runs.pop(dataset_id, None)
        self._configs.pop(dataset_id, None)
