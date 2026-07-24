from __future__ import annotations

from typing import Protocol, runtime_checkable

from fpm.domain import MeasurementWindow, Reading
from fpm.manifest import FunctionSpec


@runtime_checkable
class Adapter(Protocol):
    name: str
    version: str

    def fetch(self, fn: FunctionSpec, team: str, window: MeasurementWindow) -> Reading: ...
