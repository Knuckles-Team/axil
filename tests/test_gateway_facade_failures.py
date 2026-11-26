"""Every gateway facade method answers a failed transport with a typed result.

A timeout, a disconnect or an exception from the underlying SDK must never
reach the Qt event loop and must never read as a success.
"""

from __future__ import annotations

import httpx
import pytest

from axil.services.gateway_client import GatewayClient

_FAILURES = [
    pytest.param(httpx.ReadTimeout("timed out"), id="timeout"),
    pytest.param(httpx.ConnectError("disconnected"), id="disconnect"),
    pytest.param(RuntimeError("sdk failure"), id="sdk-exception"),
]

# (flat method name, positional arguments)
_FACADE_CALLS = [
    ("fetch_specialists", ()),
    ("run_health_check", ()),
    ("fetch_autocomplete_suggestions", ("ag",)),
    ("execute_slash_command", ("/help",)),
    ("stream_copilot_query", ("hi",)),
    ("fetch_fleet_topology", ()),
    ("fetch_fleet_approvals", ()),
    ("grant_approval", ("approval-1",)),
    ("fetch_usage_summary", ()),
    ("fetch_usage_by_model", ()),
    ("fetch_usage_tools", ()),
    ("fetch_usage_activity", ()),
    ("fetch_usage_sessions", ()),
    ("fetch_usage_traces", ()),
]


class _FailingTransport:
    """Stands in for the SDK routes and the direct HTTP pool: every call fails."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def __getattr__(self, name: str):
        error = self._error

        async def _fail(*args, **kwargs):
            raise error

        return _fail

    def stream(self, *args, **kwargs):
        raise self._error


def _client(error: Exception) -> GatewayClient:
    client = GatewayClient("http://localhost:8000", allow_insecure_http=True)
    client._sdk = _FailingTransport(error)  # type: ignore[assignment]
    client._direct_http = _FailingTransport(error)  # type: ignore[assignment]
    return client


def _is_success_payload(value: object) -> bool:
    """A failed call must come back empty, or carry an error/offline marker."""
    if isinstance(value, dict):
        if (
            value.get("enabled") is False
        ):  # the typed offline default of the traces facade
            return False
        return bool(value) and not any(k in value for k in ("error", "result"))
    if isinstance(value, list):
        return bool(value)
    return value is not None


@pytest.mark.asyncio
@pytest.mark.spec("AXIL-CLIENT-R005.3")
@pytest.mark.parametrize("error", _FAILURES)
@pytest.mark.parametrize(("method", "args"), _FACADE_CALLS)
async def test_facade_method_returns_typed_result_on_failure(
    method, args, error
) -> None:
    client = _client(error)
    result = await getattr(client, method)(*args)
    assert not _is_success_payload(result), f"{method} reported success on {error!r}"


@pytest.mark.asyncio
@pytest.mark.spec("AXIL-CLIENT-R005.3")
async def test_healthy_transport_is_not_mistaken_for_a_failure() -> None:
    client = GatewayClient("http://localhost:8000", allow_insecure_http=True)

    class _Healthy:
        async def fleet_topology(self):
            return {"workers": ["a"]}

    client._sdk = _Healthy()  # type: ignore[assignment]
    assert _is_success_payload(await client.fetch_fleet_topology())
