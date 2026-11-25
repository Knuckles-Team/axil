"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Fleet supervisor facade for the desktop gateway client.

Wraps the fleet routes of :class:`axil.services.gateway_routes.GatewayRoutes`
with the desktop's graceful-offline contract: every method swallows
transport errors and returns a typed safe default so the Qt event loop
never sees an exception from a missing gateway.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from axil.services.gateway_client import GatewayClient

logger = logging.getLogger("axil.gateway")


class FleetFacade:
    """Facade methods over the gateway's fleet routes."""

    def __init__(self, client: GatewayClient) -> None:
        self._client = client

    async def fetch_fleet_topology(self) -> dict[str, Any]:
        """Fetch the fleet/worker placement topology (OS-5.10)."""
        try:
            return await self._client._sdk.fleet_topology()
        except Exception as e:
            logger.warning(
                "Fleet topology fetch failed: error_type=%s", type(e).__name__
            )
            return {}

    async def fetch_fleet_approvals(self) -> list[dict[str, Any]]:
        """Fetch pending ActionPolicy approvals awaiting a human decision (OS-5.24)."""
        try:
            return await self._client._sdk.fleet_approvals()
        except Exception as e:
            logger.warning(
                "Fleet approvals fetch failed: error_type=%s", type(e).__name__
            )
            return []

    async def grant_approval(self, approval_id: str) -> dict[str, Any]:
        """Grant a pending fleet approval by id."""
        try:
            return await self._client._sdk.grant_approval(approval_id)
        except Exception as e:
            logger.warning("Grant approval failed: error_type=%s", type(e).__name__)
            return {"error": "Approval request failed"}
