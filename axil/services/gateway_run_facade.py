"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Run harness read facade for the desktop gateway client.

Wraps the registered ``runs.get`` and ``runs.metrics`` Arbora read
operations (ARBORA-OPS-R021.4) with the desktop's graceful-offline
contract. A typed gateway denial (a ``status: "failed"`` envelope)
passes through unchanged so the caller can classify a refusal from an
authenticated empty result; registry preflight failures, transport
errors, and malformed envelopes resolve to the typed unavailable
default so the Qt event loop never sees an exception from a missing or
refused run read.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from axil.services.gateway_client import GatewayClient

logger = logging.getLogger("axil.gateway")

#: The served run read operations and their routes.
RUNS_GET_OPERATION = "runs.get"
RUNS_GET_PATH = "/api/v1/ops/runs.get"
RUNS_METRICS_OPERATION = "runs.metrics"
RUNS_METRICS_PATH = "/api/v1/ops/runs.metrics"


class RunFacade:
    """Facade methods over the gateway's served run read operations."""

    def __init__(self, client: GatewayClient) -> None:
        self._client = client

    async def fetch_run_summary(self, run_id: str) -> dict[str, Any]:
        """Fetch one run's summary and plan snapshot, or the unavailable default."""
        return await self._invoke(RUNS_GET_OPERATION, RUNS_GET_PATH, {"run_id": run_id})

    async def fetch_run_metrics(self, run_id: str) -> dict[str, Any]:
        """Fetch one run's labelled cost aggregates, or the unavailable default."""
        return await self._invoke(
            RUNS_METRICS_OPERATION, RUNS_METRICS_PATH, {"run_id": run_id}
        )

    async def _invoke(
        self, operation: str, path: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        registry = self._client.operation_registry
        if registry is None:
            return self._unavailable("operation registry is unavailable")
        try:
            entry = registry.lookup(operation)
        except Exception as e:
            logger.warning(
                "Run op unregistered: operation=%s error_type=%s",
                operation,
                type(e).__name__,
            )
            return self._unavailable("operation not registered")
        try:
            return await self._client.invoke_operation(
                entry.operation,
                entry.digest,
                path=path,
                method=entry.method,
                payload=payload,
            )
        except Exception as e:
            logger.warning(
                "Run fetch failed: operation=%s error_type=%s",
                operation,
                type(e).__name__,
            )
            return self._unavailable(type(e).__name__)

    @staticmethod
    def _unavailable(reason: str) -> dict[str, Any]:
        return {
            "error": f"run read unavailable ({reason})",
            "code": "CLIENT_UNAVAILABLE",
        }
