"""Line patterns for persisted machine paths and internal endpoints.

The persisted-path-field matcher, the neutral-URI exemption, and the
internal-endpoint (bare-hostname) patterns the runtime-source pass scans
with.
"""

from __future__ import annotations

import re

from privacy_gate_hostnames import _is_reserved_hostname

_PERSISTED_FIELD_RE = re.compile(
    r"[\"']?(?P<field>workspace_path|source_path|skill_path|local_path|source_file|"
    r"eg_ledger_path)[\"']?\s*[:=]\s*(?P<value>.+)",
    re.IGNORECASE,
)
_NEUTRAL_URI_RE = re.compile(
    r"^[\s\"']*(?:repo|skill|connector|design)://", re.IGNORECASE
)
_INTERNAL_ENDPOINT_RE = re.compile(
    r"(?i)\b(?:[A-Za-z0-9-]+\.)+(?:arpa|internal)\b|"
    r"\b(?:[A-Za-z0-9-]+\.)*svc\.cluster\.local\b|"
    r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|"
    r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"
)
# BUG-241: the internal-endpoint pass used to be ``_SOURCE_INTERNAL_URL_RE``,
# which required a URL scheme (``https?://``) before the host -- so a BARE
# hostname literal (no ``scheme://`` prefix at all, e.g. a YAML
# ``ingress_host: example-arbora.arpa`` value or a Python string literal
# ``"example-vllm.arpa"``) was structurally invisible to it. A scheme is not
# what makes a hostname sensitive; the hostname is. This pattern drops the
# scheme requirement entirely and matches the hostname shape wherever it
# appears on the line -- inside a URL, a bare literal, an f-string, a YAML
# scalar, all of it -- covering the same suffix family the docs-path
# ``_INTERNAL_ENDPOINT_RE`` already recognizes bare (``.arpa``/``.internal``)
# plus the two extra suffixes (``.corp``/``.lan``) the old scheme-gated
# pattern additionally covered, so nothing already-caught regresses. At
# least one label must precede ``arpa``/``internal``/``corp``/``lan`` (a
# bare "internal" is an ordinary English word, not a hostname), while the
# three-label Kubernetes cluster-DNS suffix (``svc``, ``cluster``, ``local``)
# is specific enough on its own to match with zero or more leading labels,
# same as the docs-path pattern.
#
# Deliberately CASE-SENSITIVE on the suffix (no ``(?i)``): a first corpus run
# of this pattern with ``(?i)`` produced 19 false positives, every one of
# them ``DataClassification.INTERNAL``/``SomeEnum.INTERNAL`` -- a Python
# UPPER_SNAKE_CASE enum member access, not a hostname (``DataClassification``
# is itself a syntactically valid DNS label, so nothing about the identifier
# shape alone rules it out). Every genuine hostname literal in this corpus,
# real or synthetic, is written lowercase (``example-arbora.arpa``,
# ``example-vllm.arpa``, ``example-host.docker.internal``,
# ``example-model.internal``, ...) -- matching DNS/hostname
# convention -- while every enum-attribute access in this codebase is
# UPPER_SNAKE_CASE by convention, so requiring an exact-case lowercase
# suffix separates the two shapes cleanly without a Python-syntax-aware
# parse. The preceding label(s) stay case-insensitive (a hostname label
# itself may legitimately mix case), only the fixed suffix word is
# case-locked.
_HOSTNAME_LABEL_RE = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
_BARE_INTERNAL_HOSTNAME_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"(?:"
    rf"(?:{_HOSTNAME_LABEL_RE}\.)+(?:arpa|internal|corp|lan)"
    r"|"
    rf"(?:{_HOSTNAME_LABEL_RE}\.)*svc\.cluster\.local"
    r")"
    r"(?![A-Za-z0-9_.-])"
)


def _internal_endpoint_in_line(line: str) -> bool:
    """True if ``line`` contains a non-reserved internal-hostname literal.

    Scans EVERY candidate match, not just the first, so a reserved
    placeholder earlier on the line (e.g. ``example-host-prod.internal.arpa``
    used in an adversarial-fixture comment) never masks a real leak later on
    the same line.
    """
    return any(
        not _is_reserved_hostname(match.group(0))
        for match in _BARE_INTERNAL_HOSTNAME_RE.finditer(line)
    )
