"""CONCEPT:MERISTEM-ECO.mcp.usage-cost-observability-surface
Usage, cost, and observability facade for the desktop gateway client.

Wraps the :class:`axil.services.gateway_observation.ObservabilityRoutes`
route family with the desktop's graceful-offline contract: every method
swallows transport errors and returns a typed safe default so the Qt
event loop never sees an exception from a missing gateway.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from axil.services.gateway_client import GatewayClient

logger = logging.getLogger("axil.gateway")


class UsageFacade:
    """Facade methods over the gateway's observability routes."""

    def __init__(self, client: GatewayClient) -> None:
        self._client = client

    async def fetch_usage_summary(self, **f: Any) -> dict[str, Any]:
        try:
            return await self._client._obs.usage_summary(**f)
        except Exception as e:
            logger.warning(
                "Usage summary fetch failed: error_type=%s", type(e).__name__
            )
            return {}

    async def fetch_usage_by_model(self, **f: Any) -> list[dict[str, Any]]:
        try:
            return await self._client._obs.usage_by_model(**f)
        except Exception as e:
            logger.warning(
                "Usage by-model fetch failed: error_type=%s", type(e).__name__
            )
            return []

    async def fetch_usage_tools(self, **f: Any) -> list[dict[str, Any]]:
        try:
            return await self._client._obs.analytics_tools(**f)
        except Exception as e:
            logger.warning("Usage tools fetch failed: error_type=%s", type(e).__name__)
            return []

    async def fetch_usage_activity(self, **f: Any) -> list[dict[str, Any]]:
        try:
            return await self._client._obs.analytics_activity(**f)
        except Exception as e:
            logger.warning(
                "Usage activity fetch failed: error_type=%s", type(e).__name__
            )
            return []

    async def fetch_usage_sessions(self, **f: Any) -> list[dict[str, Any]]:
        try:
            return await self._client._obs.usage_top_sessions(**f)
        except Exception as e:
            logger.warning(
                "Usage sessions fetch failed: error_type=%s", type(e).__name__
            )
            return []

    async def fetch_usage_traces(self) -> dict[str, Any]:
        try:
            return await self._client._obs.usage_traces()
        except Exception as e:
            logger.warning("Usage traces fetch failed: error_type=%s", type(e).__name__)
            return {"enabled": False, "traces": []}
