"""Usage, cost, and observability routes served by the arbora gateway.

CONCEPT:MERISTEM-ECO.mcp.usage-cost-observability-surface

Split out of :mod:`axil.services.gateway_routes` so the cockpit's
usage/cost panel keeps one small route family; the desktop facade methods
that wrap these routes with their graceful-offline defaults live in
:class:`axil.services.gateway_usage_facade.UsageFacade`.
"""

from __future__ import annotations

from typing import Any

from axil.services.gateway_routes import GatewayHttp


class ObservabilityRoutes(GatewayHttp):
    """The ``/api/observability`` route family."""

    async def usage_summary(self, **filters: Any) -> dict[str, Any]:
        return self._as_dict(await self._get("/api/observability/summary", filters))

    async def usage_by_model(self, **filters: Any) -> list[dict[str, Any]]:
        return self._as_list(await self._get("/api/observability/by-model", filters))

    async def analytics_tools(self, **filters: Any) -> list[dict[str, Any]]:
        return self._as_list(
            await self._get("/api/observability/analytics/tools", filters)
        )

    async def analytics_activity(self, **filters: Any) -> list[dict[str, Any]]:
        return self._as_list(
            await self._get("/api/observability/analytics/activity", filters)
        )

    async def usage_top_sessions(
        self, *, limit: int = 20, **filters: Any
    ) -> list[dict[str, Any]]:
        return self._as_list(
            await self._get(
                "/api/observability/top-sessions", {"limit": limit, **filters}
            )
        )

    async def usage_traces(self, **filters: Any) -> dict[str, Any]:
        body = await self._get("/api/observability/traces", filters)
        return body if isinstance(body, dict) else {"enabled": False, "traces": []}
