"""
CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Service layer for communicating with the arbora gateway.

Thin axil-facing facade over the gateway routes, so transport lives in
one place. This facade preserves axil's graceful-offline contract: every
method swallows transport errors and returns a safe default so the Qt
event loop never sees an exception from a missing gateway.

The route families live in their own modules:
:class:`axil.services.gateway_routes.GatewayRoutes` (agent, copilot, and
fleet routes plus the ``/stream`` channel),
:class:`axil.services.gateway_observation.ObservabilityRoutes` (usage and
cost), and one facade class per family in the
``gateway_*_facade`` modules. :class:`GatewayClient` keeps the endpoint
validation, the registered-operation transport, and the pooled HTTP
client; per-family behavior is exposed both namespaced (``client.usage``)
and flat (``client.fetch_usage_summary``) for the panels that predate the
namespaces.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from axil.services.gateway_copilot_facade import CopilotFacade
from axil.services.gateway_dashboard_facade import DashboardFacade
from axil.services.gateway_envelope import (
    GRAPH_ROUTES as _GRAPH_ROUTES,  # noqa: F401  (legacy test-facing alias)
)
from axil.services.gateway_envelope import (
    MAX_RESPONSE_BYTES,
    decode_envelope,
    endpoint_is_invalid,
    is_failed_envelope,
    plaintext_requires_optin,
    tls_verify,
)
from axil.services.gateway_extraction_facade import ExtractionFacade
from axil.services.gateway_fleet_facade import FleetFacade
from axil.services.gateway_graph_facade import GraphFacade
from axil.services.gateway_market_facade import MarketFacade
from axil.services.gateway_observation import ObservabilityRoutes
from axil.services.gateway_routes import GatewayRoutes
from axil.services.gateway_run_facade import RunFacade
from axil.services.gateway_usage_facade import UsageFacade
from axil.services.gateway_voice_facade import VoiceFacade
from axil.services.operation_registry import OperationRegistry, OperationRegistryError

logger = logging.getLogger("axil.gateway")

DEFAULT_BASE_URL = "http://localhost:8000"


class GatewayClient:
    """Axil-facing gateway facade: endpoint validation, registered
    operation transport, and namespaced route facades with a flat API."""

    # Flat method name -> facade attribute. Panels keep calling the flat
    # names; new code should use the namespaced facades directly.
    _FLAT_API: dict[str, str] = {
        "dashboard_layout": "dashboard",
        "dashboard_data": "dashboard",
        "fetch_specialists": "copilot",
        "run_health_check": "copilot",
        "fetch_autocomplete_suggestions": "copilot",
        "execute_slash_command": "copilot",
        "stream_copilot_query": "copilot",
        "fetch_fleet_topology": "fleet",
        "fetch_fleet_approvals": "fleet",
        "grant_approval": "fleet",
        "fetch_usage_summary": "usage",
        "fetch_usage_by_model": "usage",
        "fetch_usage_tools": "usage",
        "fetch_usage_activity": "usage",
        "fetch_usage_sessions": "usage",
        "fetch_usage_traces": "usage",
        "submit_and_stream_extraction": "extraction",
        "fetch_extraction_jsonl": "extraction",
        "ask_data": "graph",
        "nl_query": "graph",
        "graph_query": "graph",
        "promql": "graph",
        "kvcache_stats": "graph",
        "federated_search": "graph",
        "transcribe_voice": "voice",
        "fetch_market_ticks": "market",
        "fetch_run_summary": "run",
        "fetch_run_metrics": "run",
    }

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        allow_insecure_http: bool = False,
        operation_registry: OperationRegistry | None = None,
    ):
        if endpoint_is_invalid(base_url):
            raise ValueError("Gateway endpoint is invalid")
        if plaintext_requires_optin(base_url, allow_insecure_http):
            raise ValueError("Plaintext gateway transport requires explicit opt-in")

        self.base_url = str(base_url).rstrip("/")
        # The application loads the installed generated registry once and injects
        # the same immutable view into its gateway client. Direct test/utility
        # clients may omit it until they opt into a registered operation call.
        self.operation_registry = operation_registry
        # One pooled SDK client for the app's lifetime (desktop singleton).
        self._sdk = GatewayRoutes(self.base_url, timeout=15.0, verify=tls_verify())
        self._obs = ObservabilityRoutes(
            self.base_url, timeout=15.0, verify=tls_verify()
        )
        self._direct_http = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(120.0, connect=10.0),
            verify=tls_verify(),
            limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
        )

        # Route-family facades. Each holds this client and resolves the
        # pooled transports at call time, so tests can swap
        # ``_direct_http``/``_sdk`` on the instance without re-wiring.
        self.copilot = CopilotFacade(self)
        self.dashboard = DashboardFacade(self)
        self.fleet = FleetFacade(self)
        self.usage = UsageFacade(self)
        self.extraction = ExtractionFacade(self)
        self.graph = GraphFacade(self)
        self.voice = VoiceFacade(self)
        self.market = MarketFacade(self)
        self.run = RunFacade(self)

    def __getattr__(self, name: str) -> Any:
        """Serve the legacy flat API from the namespaced facades."""
        facade = self._FLAT_API.get(name)
        if facade is None:
            raise AttributeError(name)
        return getattr(getattr(self, facade), name)

    @staticmethod
    async def _bounded_body(
        response: httpx.Response, *, limit: int = MAX_RESPONSE_BYTES
    ) -> bytes:
        declared = response.headers.get("content-length")
        if declared:
            try:
                if int(declared) > limit:
                    raise RuntimeError("Gateway response exceeded its size limit")
            except ValueError as exc:
                raise RuntimeError("Gateway response length was invalid") from exc
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body.extend(chunk)
            if len(body) > limit:
                raise RuntimeError("Gateway response exceeded its size limit")
        return bytes(body)

    async def _json_request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        operation: str | None = None,
        digest: str | None = None,
    ) -> dict[str, Any]:
        if operation is not None or digest is not None:
            if operation is None or digest is None:
                raise OperationRegistryError(
                    "registered operation calls require an operation and digest"
                )
            self._validate_operation(operation, digest, method=method)
        async with self._direct_http.stream(
            method, path, json=payload, follow_redirects=False
        ) as response:
            body = await self._bounded_body(response)
            value = decode_envelope(body)
            # The gateway answers a typed failed operation with its
            # public HTTP status (400/403/500/503) and a ``{"status":
            # "failed"}`` envelope. That envelope is the tool's answer, not a
            # transport error, so it is returned for the caller to classify.
            if not (response.is_error and is_failed_envelope(value)):
                response.raise_for_status()
        if value is None:
            raise RuntimeError("Gateway returned an invalid envelope")
        return value

    def _validate_operation(self, operation: str, digest: str, *, method: str) -> None:
        """Validate an operation against the injected registry before transport."""
        if self.operation_registry is None:
            raise OperationRegistryError("operation registry is unavailable")
        entry = self.operation_registry.lookup(operation)
        self.operation_registry.validate_digest(operation, digest)
        if entry.method.upper() != method.upper():
            raise OperationRegistryError(
                f"method mismatch for operation {operation!r}: "
                f"expected {entry.method.upper()}, got {method.upper()}"
            )

    async def invoke_operation(
        self,
        operation: str,
        digest: str,
        *,
        path: str,
        method: str = "POST",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke one registered Arbora operation through the existing transport.

        Registry validation deliberately happens inside ``_json_request`` before
        opening the HTTP stream. Unknown operations, digest mismatches, missing
        registry injection, and method mismatches therefore return the same
        typed unavailable result without any network effect.
        """
        try:
            return await self._json_request(
                method,
                path,
                payload=payload,
                operation=operation,
                digest=digest,
            )
        except OperationRegistryError as exc:
            logger.warning(
                "Arbora operation rejected before transport: "
                "operation=%s error_type=%s",
                operation,
                type(exc).__name__,
            )
            return {
                "error": "Arbora operation unavailable",
                "code": "CLIENT_UNAVAILABLE",
            }

    async def aclose(self) -> None:
        """Release the direct HTTP pool and the shared SDK when supported."""

        await self._direct_http.aclose()
        close = getattr(self._sdk, "aclose", None)
        if callable(close):
            await close()
        await self._obs.aclose()
