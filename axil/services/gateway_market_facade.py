"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Market data facade for the desktop gateway client.

Wraps the registered ``markets.ticks`` Arbora operation with the
desktop's graceful-offline contract: registry preflight happens before
any transport, and every failure mode (missing registry, unregistered
operation, digest mismatch, transport error, malformed envelope, or a
typed gateway denial) is swallowed into the typed unavailable default so
the Qt event loop never sees an exception from a missing or refused
markets route.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from axil.services.gateway_client import GatewayClient

logger = logging.getLogger("axil.gateway")

#: The served markets operation and its route (ARBORA-OPS-R017 family).
MARKETS_TICKS_OPERATION = "markets.ticks"
MARKETS_TICKS_PATH = "/api/v1/ops/markets.ticks"


class MarketFacade:
    """Facade methods over the gateway's served markets operations."""

    def __init__(self, client: GatewayClient) -> None:
        self._client = client

    async def fetch_market_ticks(
        self, symbol: str, *, limit: int = 40
    ) -> dict[str, Any]:
        """Fetch the served tick series for one symbol.

        Returns the gateway envelope on success (``{"status":
        "success", "result": {...}}``) or the typed unavailable default
        when the route cannot be reached or is refused.
        """
        registry = self._client.operation_registry
        if registry is None:
            return self._unavailable("operation registry is unavailable")
        try:
            entry = registry.lookup(MARKETS_TICKS_OPERATION)
        except Exception as e:
            logger.warning(
                "Market ticks op unregistered: error_type=%s", type(e).__name__
            )
            return self._unavailable("operation not registered")
        try:
            return await self._client.invoke_operation(
                entry.operation,
                entry.digest,
                path=MARKETS_TICKS_PATH,
                method=entry.method,
                payload={"symbol": symbol, "limit": limit},
            )
        except Exception as e:
            logger.warning("Market ticks fetch failed: error_type=%s", type(e).__name__)
            return self._unavailable(type(e).__name__)

    @staticmethod
    def _unavailable(reason: str) -> dict[str, Any]:
        return {
            "error": f"markets route unavailable ({reason})",
            "code": "CLIENT_UNAVAILABLE",
        }
