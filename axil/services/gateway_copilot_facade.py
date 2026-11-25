"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Copilot and agent facade for the desktop gateway client.

Wraps the agent/copilot routes of :class:`axil.services.gateway_routes.GatewayRoutes`
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


def emit_copilot_progress(ev_type: str, event: dict[str, Any], progress_cb) -> None:
    """Forward one non-final-output copilot event to progress_cb, if any."""
    if not progress_cb:
        return
    if ev_type == "thought":
        progress_cb(f"💭 {event.get('thought', '')}")
    elif ev_type == "call_tool":
        progress_cb(f"🛠️ Tool: {event.get('tool', '')}")
    else:
        progress_cb(
            f"📡 {ev_type}: {event.get('message', '') or event.get('error', '')}"
        )


class CopilotFacade:
    """Facade methods over the gateway's copilot and agent routes."""

    def __init__(self, client: GatewayClient) -> None:
        self._client = client

    async def fetch_specialists(self):
        """Fetch all specialists from the Knowledge Graph via the Gateway."""
        try:
            return await self._client._sdk.list_agents()
        except Exception as e:
            logger.warning(
                "Failed to fetch specialists: error_type=%s", type(e).__name__
            )
            return []

    async def run_health_check(self):
        """Run health check against the centralized Gateway."""
        try:
            data = await self._client._sdk.maintenance_status()
            return {
                "status": "success",
                "result": f"Gateway healthy. Maintenance Required: {data.get('maintenance_required', False)}",
            }
        except Exception as e:
            logger.warning(
                "Gateway health check failed: error_type=%s", type(e).__name__
            )
            return {"status": "error", "result": "❌ central Gateway offline."}

    async def fetch_autocomplete_suggestions(self, query: str):
        """Fetch autocomplete suggestions for slash commands."""
        try:
            return await self._client._sdk.autocomplete(query)
        except Exception as e:
            logger.debug("Autocomplete fetch failed: error_type=%s", type(e).__name__)
            return []

    async def execute_slash_command(self, query: str):
        """Execute a slash command on the gateway."""
        try:
            return await self._client._sdk.execute_command(query)
        except Exception as e:
            return {
                "result": "❌ Gateway connection failed. Falling back to local run is not supported for slash commands."
            }

    async def stream_copilot_query(self, query: str, progress_cb=None):
        """Execute master copilot query with streaming output."""
        try:
            final_output = ""
            async for event in self._client._sdk.stream(
                query, mode="ask", topology="basic", timeout=60.0
            ):
                ev_type = str(event.get("type") or "")
                if ev_type == "final_output":
                    final_output = event.get("content", "")
                else:
                    emit_copilot_progress(ev_type, event, progress_cb)
            if final_output:
                return {"result": final_output}
        except Exception as e:
            logger.warning(
                "Gateway SSE execution failed: error_type=%s", type(e).__name__
            )

        return {
            "result": "❌ Gateway is offline. Please make sure the arbora gateway is running at http://localhost:8000."
        }
