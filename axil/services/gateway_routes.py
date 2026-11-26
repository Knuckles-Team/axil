"""Typed access to the Arbora gateway's REST routes and its ``/stream`` channel.

Arbora 0.1.2 no longer publishes a hand-written gateway client (its generated
operation client replaced it), so Axil keeps the few route calls its
desktop panels use here. Each method unwraps the JSON body and returns a safe
empty value when the gateway answers with an unexpected shape. Transport and
HTTP errors raise; :class:`axil.services.gateway_client.GatewayClient`
catches them and returns typed offline results to the UI.

The shared transport lives in :class:`GatewayHttp`; the agent, copilot, and
fleet routes the cockpit uses directly live in :class:`GatewayRoutes`, and
the observability routes live in
:class:`axil.services.gateway_observation.ObservabilityRoutes`.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

DEFAULT_GATEWAY_URL = "http://localhost:8000"


class GatewayHttp:
    """Pooled HTTP transport shared by every gateway route family."""

    def __init__(
        self,
        base_url: str = DEFAULT_GATEWAY_URL,
        *,
        timeout: float = 30.0,
        verify: Any = True,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            verify=verify,
            transport=transport,
            follow_redirects=False,
        )

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = await self._http.get(path, params=params or None)
        response.raise_for_status()
        return response.json()

    async def _post(self, path: str, payload: dict[str, Any]) -> Any:
        response = await self._http.post(path, json=payload)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _as_dict(body: Any) -> dict[str, Any]:
        return body if isinstance(body, dict) else {}

    @staticmethod
    def _as_list(body: Any) -> list[dict[str, Any]]:
        return body if isinstance(body, list) else []

    async def aclose(self) -> None:
        await self._http.aclose()


class GatewayRoutes(GatewayHttp):
    """Agent, copilot, and fleet routes plus the ``/stream`` SSE channel."""

    async def list_agents(self) -> list[dict[str, Any]]:
        body = await self._get("/api/enhanced/agents")
        if isinstance(body, dict) and body.get("status") == "ok":
            return list(body.get("agents", []))
        return []

    async def maintenance_status(self) -> dict[str, Any]:
        return self._as_dict(await self._get("/api/enhanced/maintenance/status"))

    async def autocomplete(self, query: str) -> list[str]:
        body = await self._get("/api/enhanced/commands/autocomplete", {"query": query})
        return list(body.get("suggestions", [])) if isinstance(body, dict) else []

    async def execute_command(self, command: str) -> dict[str, Any]:
        body = await self._post("/api/enhanced/commands/execute", {"command": command})
        if not isinstance(body, dict):
            return {"result": ""}
        return {
            "result": body.get("response_markdown", ""),
            "client_actions": body.get("client_actions", []),
        }

    async def fleet_topology(self) -> dict[str, Any]:
        return self._as_dict(await self._get("/api/fleet/topology"))

    async def fleet_approvals(self) -> list[dict[str, Any]]:
        body = await self._get("/api/fleet/approvals")
        if isinstance(body, dict):
            return list(body.get("approvals", []))
        return self._as_list(body)

    async def grant_approval(self, approval_id: str) -> dict[str, Any]:
        return self._as_dict(
            await self._post("/api/fleet/approvals/grant", {"approval_id": approval_id})
        )

    async def stream(
        self,
        query: str,
        *,
        mode: str = "ask",
        topology: str = "basic",
        timeout: float = 120.0,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream an agent run over ``/stream``, yielding each parsed SSE event."""
        async with self._http.stream(
            "POST",
            "/stream",
            json={"query": query, "mode": mode, "topology": topology},
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    yield json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
