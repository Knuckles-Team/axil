"""CONCEPT:MERISTEM-GBOT.cockpit.through-gbot
Shared helpers for the gateway transport and its response envelopes.

Endpoint validation, TLS context construction, and the envelope decoding
helpers every gateway route facade shares. The desktop client never talks
to the gateway directly through these; they are the common substrate of
the route and facade modules in this package.
"""

from __future__ import annotations

import ipaddress
import json
import re
import ssl
from typing import Any
from urllib.parse import urlsplit

# Hard caps for streamed gateway traffic (see the extraction and copilot
# facades that consume SSE bodies).
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_STREAM_EVENTS = 100_000
MAX_STREAM_LINE_BYTES = 256 * 1024

#: Job ids the extraction routes accept; anything else is refused.
SAFE_JOB_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

#: Graph routes the desktop may POST to; anything else is refused.
GRAPH_ROUTES = frozenset(
    {
        "ask-data",
        "nl-query",
        "query",
        "promql",
        "kvcache",
        "federated-search",
    }
)


def is_local_host(host: str) -> bool:
    """True when `host` names loopback, a link-local, or a .local host.

    Plaintext (http://) gateway calls are only allowed against these so a
    misconfigured endpoint can never leak prompts or credentials in
    cleartext to a remote host.
    """
    if host in {"localhost", "127.0.0.1", "[::1]", "::1"}:
        return True
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return host.endswith(".local")
    return addr.is_loopback or addr.is_link_local or addr.is_private


def tls_verify() -> ssl.SSLContext | bool:
    """TLS verification policy for the pooled gateway HTTP clients."""
    return ssl.create_default_context() if "https" else True


def decode_envelope(body: bytes) -> dict[str, Any] | None:
    """Parse one gateway response body into its JSON envelope, if possible.

    Returns None when the body is not a JSON object so callers can refuse
    the reply instead of treating malformed output as an empty result.
    """
    if not body:
        return None
    try:
        value = json.loads(body)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def is_failed_envelope(value: dict[str, Any] | None) -> bool:
    """True when a typed operation answered with its public failure envelope."""
    if value is None:
        return False
    return value.get("status") == "failed"


def endpoint_is_invalid(url: str) -> bool:
    """Validate a gateway endpoint URL.

    Rejects non-http(s) schemes, missing hosts, userinfo, query strings,
    and fragments: the client must never follow a crafted redirect or leak
    a token through a query string.
    """
    parsed = urlsplit(str(url).strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return True
    if parsed.username is not None or parsed.password is not None:
        return True
    return bool(parsed.query) or bool(parsed.fragment)


def plaintext_requires_optin(url: str, allow_insecure_http: bool) -> bool:
    """True when a plaintext endpoint needs an explicit opt-in flag."""
    if allow_insecure_http:
        return False
    parsed = urlsplit(str(url).strip())
    return parsed.scheme.lower() == "http" and not is_local_host(
        (parsed.hostname or "").lower().rstrip(".")
    )
