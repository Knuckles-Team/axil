"""Line classification for the tracked-privacy gate.

Turns one line of text into the set of leak categories it carries:
persisted machine paths, real home paths, local identifiers, machine host
ids, and -- for deployment docs -- internal endpoints, credential URIs, and
remote-account identities. Runtime source gets the concrete-leak categories
without the public-doc path heuristics.
"""

from __future__ import annotations

import re
from pathlib import Path

from privacy_gate_credentials import (
    _CREDENTIAL_URI_RE,
    _HOST_IDENTITY_RE,
    _MACHINE_HOST_ID_RE,
    _PRIVATE_KEY_LINE_RE,
    _is_credential_exempt,
)
from privacy_gate_home_paths import _has_real_home_path
from privacy_gate_patterns import (
    _INTERNAL_ENDPOINT_RE,
    _NEUTRAL_URI_RE,
    _PERSISTED_FIELD_RE,
    _internal_endpoint_in_line,
)


def _is_deployment_doc(path: Path) -> bool:
    value = path.as_posix().casefold()
    return value.startswith("docs/recipes/") or any(
        marker in value
        for marker in (
            "deploy",
            "runbook",
            "configuration",
            "workspace-config",
            "mcp_auth",
            "secrets-auth",
        )
    )


def _persisted_machine_path_category(line: str) -> str | None:
    persisted = _PERSISTED_FIELD_RE.search(line)
    if not persisted or _NEUTRAL_URI_RE.search(persisted.group("value")):
        return None
    value = persisted.group("value").strip(" \t,;)}]\"'").casefold()
    field = persisted.group("field")
    # A shell/template interpolation placeholder (``${WORKSPACE_ROOT}``, closing
    # brace already stripped above) is resolved at runtime by whatever consumes
    # the file, never a baked-in machine path — safe regardless of the field's
    # own casing, same reasoning as the existing uppercase-field exemption.
    is_template_placeholder = value.startswith("${")
    runtime_relative = (field.isupper() or is_template_placeholder) and not re.match(
        r"^(?:[a-z]:|[/\\]|~)", value, re.IGNORECASE
    )
    if value in {"", "none", "null", "unset"} or runtime_relative:
        return None
    return "persisted machine path"


def _identifier_hit(line: str, identifiers: frozenset[str]) -> bool:
    folded = line.casefold()
    return any(
        re.search(rf"(?<![\w-]){re.escape(value)}(?![\w-])", folded)
        for value in identifiers
    )


def _deployment_doc_categories(line: str, deployment_doc: bool) -> set[str]:
    categories: set[str] = set()
    if not deployment_doc:
        return categories
    if _INTERNAL_ENDPOINT_RE.search(line):
        categories.add("hard-coded internal endpoint")
    credential_match = _CREDENTIAL_URI_RE.search(line)
    if credential_match and not _is_credential_exempt(credential_match):
        categories.add("credential-bearing URI")
    if _HOST_IDENTITY_RE.search(line):
        categories.add("hard-coded remote account")
    return categories


def classify_line(
    line: str,
    *,
    identifiers: frozenset[str],
    deployment_doc: bool,
) -> frozenset[str]:
    categories: set[str] = set()
    persisted_category = _persisted_machine_path_category(line)
    if persisted_category is not None:
        categories.add(persisted_category)
    elif _has_real_home_path(line):
        categories.add("machine-specific home path")
    if _identifier_hit(line, identifiers):
        categories.add("local account or host identifier")
    if _MACHINE_HOST_ID_RE.search(line):
        categories.add("machine-specific host identifier")
    categories.update(_deployment_doc_categories(line, deployment_doc))
    return frozenset(categories)


def classify_runtime_source_line(
    line: str, *, identifiers: frozenset[str]
) -> frozenset[str]:
    """Classify runtime/deployment source without applying public-doc path heuristics.

    Source code legitimately manipulates path-shaped values, so the generic
    ``source_path = ...`` rule would be noisy here. Concrete account paths,
    environment endpoints, credential-bearing URLs, and local identities are
    never legitimate package defaults and are checked for every shipped
    runtime and deployment file instead.

    D-CIP-10: the categories below used to be suffixed ``in changed source``,
    from when :func:`privacy_gate_artifacts._runtime_source_artifacts` only
    looked at ``git diff``. That scope was the bug; the label is now
    ``in runtime source`` so the gate's own output cannot imply a narrower
    guarantee than it actually gives.
    """
    categories: set[str] = set()
    if _has_real_home_path(line):
        categories.add("machine-specific home path in runtime source")
    folded = line.casefold()
    if any(
        re.search(rf"(?<![\w-]){re.escape(value)}(?![\w-])", folded)
        for value in identifiers
    ):
        categories.add("local account or host identifier in runtime source")
    if _internal_endpoint_in_line(line):
        categories.add("hard-coded internal endpoint in runtime source")
    credential_match = _CREDENTIAL_URI_RE.search(line)
    if credential_match and not _is_credential_exempt(credential_match):
        categories.add("credential-bearing URI in runtime source")
    if _PRIVATE_KEY_LINE_RE.fullmatch(line):
        categories.add("private key material in runtime source")
    return frozenset(categories)
