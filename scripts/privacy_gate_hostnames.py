"""Reserved-for-documentation hostname and address recognition.

RFC 2606/6761 documentation domains, RFC 5737/3927/3849 reserved address
blocks, and localhost can never resolve to (or disclose) a real host, so a
fixture built on one of these is provably synthetic -- never a leak,
regardless of what appears before the ``://``. Recognizing them is what
keeps the widened runtime-source/credential/endpoint passes from being
noisy enough to end up in someone's SKIP= list (the exact failure mode this
widening exists to avoid repeating).
"""

from __future__ import annotations

import ipaddress

_RESERVED_DOCUMENTATION_TLDS = frozenset({"test", "example", "invalid", "localhost"})
_RESERVED_EXAMPLE_DOMAINS = frozenset({"example.com", "example.net", "example.org"})
_RESERVED_IPV4_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "127.0.0.0/8",  # RFC 5735 loopback (0.0.0.0/32 below is separate)
        "0.0.0.0/32",
        "192.0.2.0/24",  # RFC 5737 TEST-NET-1
        "198.51.100.0/24",  # RFC 5737 TEST-NET-2
        "203.0.113.0/24",  # RFC 5737 TEST-NET-3
        "169.254.0.0/16",  # RFC 3927 link-local
    )
)
_RESERVED_IPV6_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "fe80::/10",  # RFC 4291 link-local
        "2001:db8::/32",  # RFC 3849 documentation
    )
)


def _is_localhost_like(candidate: str) -> bool:
    """RFC 6761 ``localhost`` (bare or any subdomain), plus Docker Desktop's
    OWN published, universal ``host.docker.internal`` convention
    (`extra_hosts: host.docker.internal:host-gateway`, documented at
    docs.docker.com and used in millions of public docker-compose.yml files)
    -- it names no host specific to any one deployment; every Docker install
    answers to it identically. A single fixed literal, not a wildcard/prefix
    rule, so this cannot mask a genuine ``*.internal`` leak the way widening
    the general suffix match would (CX-RAT-09)."""
    return (
        candidate == "localhost"
        or candidate.endswith(".localhost")
        or candidate == "host.docker.internal"
    )


def _is_reserved_example_domain(candidate: str) -> bool:
    """RFC 2606 example.com/.net/.org (+ any subdomain), this repo's own
    leading-``example``/``example-`` label convention (BUG-241, scoped to
    the FIRST label only -- see :func:`_is_reserved_hostname`'s docstring),
    and any RFC 2606/6761 documentation TLD (``.test``/``.example``/
    ``.invalid``/``.localhost``)."""
    if candidate in _RESERVED_EXAMPLE_DOMAINS or any(
        candidate.endswith(f".{domain}") for domain in _RESERVED_EXAMPLE_DOMAINS
    ):
        return True
    labels = candidate.split(".")
    if labels[0] == "example" or labels[0].startswith("example-"):
        return True
    return labels[-1] in _RESERVED_DOCUMENTATION_TLDS


def _is_reserved_documentation_address(candidate: str) -> bool:
    """RFC 5737 (TEST-NET-1/2/3), RFC 3927 (link-local), and RFC 3849
    (IPv6 documentation) address blocks."""
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        return False
    networks = (
        _RESERVED_IPV6_NETWORKS if address.version == 6 else _RESERVED_IPV4_NETWORKS
    )
    return any(address in network for network in networks)


def _is_reserved_hostname(host: str) -> bool:
    """True for an RFC-reserved-for-documentation hostname/address.

    Covers example.com/.net/.org and any ``*.test``/``*.example``/
    ``*.invalid``/``*.localhost`` name (RFC 2606, 6761), plus the RFC
    5737/3927/3849 documentation address blocks and bare ``localhost``.

    BUG-241: also covers this repo's own extension of the RFC 2606
    convention -- a hostname whose LEADING label IS ``example`` or is
    prefixed ``example-`` (e.g. ``example-host-prod.internal.arpa``, the
    adversarial-fixture convention already used in
    ``tests/unit/mcp/test_compliance_tools.py``, and mirroring the existing
    ``_RESERVED_HOME_USERS`` "example"/"example-user" handling for home
    paths). Scoped to the FIRST label only, never any label anywhere in the
    name: a multi-label internal-looking value can legitimately carry
    "example" as an unrelated interior segment (a pre-existing fixture in
    ``tests/gates/test_docs_contract_gate.py`` builds a value with an
    interior ``example`` label ahead of the ``svc``/``cluster``/``local``
    triplet this way to prove a genuine leak is still caught) -- only the
    convention's actual signal position,
    the label that names the fake host itself, counts.
    """
    candidate = host.strip().rstrip(".").casefold()
    if not candidate:
        return False
    return (
        _is_localhost_like(candidate)
        or _is_reserved_example_domain(candidate)
        or _is_reserved_documentation_address(candidate)
    )
