"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Service dashboard facade for the desktop gateway client.

Reads the served dashboard layout and widget data over the client's
direct HTTP transport (the same transport the registered operation
calls use) and refuses malformed replies instead of rendering them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from axil.services.gateway_client import GatewayClient


class DashboardFacade:
    """Facade methods over the gateway's served dashboard routes."""

    def __init__(self, client: GatewayClient) -> None:
        self._client = client

    async def dashboard_layout(self) -> dict[str, Any]:
        """Read the served layout without importing gateway configuration."""
        value = await self._client._json_request("GET", "/api/dashboard/layout")
        if not isinstance(value.get("groups"), list):
            raise RuntimeError("Dashboard layout is unavailable")
        for group in value["groups"]:
            if not isinstance(group, dict) or not isinstance(group.get("name"), str):
                raise RuntimeError("Dashboard group is invalid")
            if not isinstance(group.get("services"), list):
                raise RuntimeError("Dashboard services are invalid")
            for service in group["services"]:
                if not isinstance(service, dict) or any(
                    not isinstance(service.get(key), str) for key in ("id", "name")
                ):
                    raise RuntimeError("Dashboard service is invalid")
                if not isinstance(service.get("visible", True), bool) or not isinstance(
                    service.get("url", ""), str
                ):
                    raise RuntimeError("Dashboard service presentation is invalid")
        return value

    async def dashboard_data(self) -> dict[str, Any]:
        """Read widget values; failed or malformed replies are not empty success."""
        value = await self._client._json_request("GET", "/api/dashboard/data")
        for widget in value.values():
            if not isinstance(widget, dict) or not isinstance(
                widget.get("status"), str
            ):
                raise RuntimeError("Dashboard widget is invalid")
            if not isinstance(widget.get("fields", {}), dict):
                raise RuntimeError("Dashboard widget fields are invalid")
            if widget.get("error") is not None and not isinstance(widget["error"], str):
                raise RuntimeError("Dashboard widget error is invalid")
        return value
