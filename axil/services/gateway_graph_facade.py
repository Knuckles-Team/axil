"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Epistemic-graph capability facade for the desktop gateway client.

CONCEPT:MERISTEM-GBOT.graph.epistemic-cypher-surface

Thin POSTs to the gateway's action-routed ``/api/graph/*`` twins — the
REST side of the arbora MCP tools nl_query / ask_data / graph_promql /
graph_kvcache / graph_federated_search (backend KG-2.305 / KG-2.308 /
KG-2.310). Every call is graceful-offline like the rest of the facade:
transport or tool errors collapse to a dict carrying an ``"error"`` key
so the Qt event loop never sees an exception from a missing
gateway/route.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from axil.services.gateway_envelope import GRAPH_ROUTES, is_failed_envelope

if TYPE_CHECKING:
    from axil.services.gateway_client import GatewayClient

logger = logging.getLogger("axil.gateway")


class GraphFacade:
    """Facade methods over the gateway's served graph routes."""

    def __init__(self, client: GatewayClient) -> None:
        self._client = client

    async def _graph_post(self, route: str, payload: dict) -> dict:
        """POST ``payload`` to ``/api/graph/{route}`` and unwrap the envelope."""
        try:
            if route not in GRAPH_ROUTES:
                raise ValueError("Gateway graph route is invalid")
            env = await self._client._json_request(
                "POST", f"/api/graph/{route}", payload=payload
            )
        except Exception as e:
            logger.warning("Graph request failed: error_type=%s", type(e).__name__)
            return {"error": "gateway offline or route unavailable"}
        if env.get("status") == "error":
            return {"error": "gateway graph request failed"}
        if is_failed_envelope(env):
            # A typed failed operation keeps its own public error, so the
            # caller shows why, not a misleading "gateway offline".
            failed = env.get("result")
            return failed if isinstance(failed, dict) else {"error": "failed"}
        result = env.get("result")
        return result if isinstance(result, dict) else {"result": result}

    async def ask_data(
        self, question: str, *, dialect: str = "auto", limit: int = 50
    ) -> dict:
        """Answer a natural-language DATA question over the KG (backend KG-2.308).

        Runs the DB-GPT-style multi-step data-analysis agent: schema-link →
        generate a read-only query → execute → self-correct → synthesize an
        answer. Returns answer + auditable query + rows + citations + trace.
        """
        return await self._graph_post(
            "ask-data", {"question": question, "dialect": dialect, "limit": limit}
        )

    async def nl_query(
        self, text: str, *, dialect: str = "auto", execute: bool = True, limit: int = 50
    ) -> dict:
        """Translate NL → one auditable read-only query and run it (backend KG-2.305).

        Set ``execute=False`` to preview the generated query without running it.
        """
        return await self._graph_post(
            "nl-query",
            {"text": text, "dialect": dialect, "execute": execute, "limit": limit},
        )

    async def graph_query(
        self, cypher: str, *, scope: str = "local", as_of: str = ""
    ) -> dict:
        """Run one read-only graph query and return its EvidenceBundle.

        The REST twin of the ``graph_query`` MCP tool. ``scope`` selects the
        dialect (``local`` Cypher | ``sql`` | ``sparql`` | ``federated``) and
        ``as_of`` pins a bitemporal instant. Result rows arrive in the bundle's
        ``evidence_spans``.
        """
        payload: dict = {"cypher": cypher, "scope": scope}
        if as_of:
            payload["as_of"] = as_of
        return await self._graph_post("query", payload)

    async def promql(self, query: str, *, action: str = "instant") -> dict:
        """Query the engine's observability metrics with PromQL (backend KG-2.310)."""
        return await self._graph_post("promql", {"query": query, "action": action})

    async def kvcache_stats(self) -> dict:
        """Shared content-addressed KV-cache occupancy + dedup counters (KG-2.310)."""
        return await self._graph_post("kvcache", {"action": "stats"})

    async def federated_search(
        self, query: str, *, top_k: int = 10, references: str = ""
    ) -> dict:
        """Federated search across registered external graphs (backend KG-2.310)."""
        payload: dict = {"query": query, "top_k": top_k}
        if references:
            payload["references"] = references
        return await self._graph_post("federated-search", payload)
