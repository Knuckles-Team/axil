"""Credential patterns, the Violation model, and content hashing.

The private-key, credential-URI, and host-identity patterns, the documented
placeholder-token vocabulary that exempts template DSNs, the neutral
package-author constants, and the ``Violation`` record the gate reports.
Findings carry a content fingerprint only -- the sensitive matched value is
never written or printed.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from privacy_gate_hostnames import _is_reserved_hostname

_PRIVATE_KEY_LINE_RE = re.compile(r"^\s*-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----\s*$")
_CREDENTIAL_URI_RE = re.compile(
    r"(?i)\b[a-z][a-z0-9+.-]*://[^\s/@:]+:(?P<secret>[^\s/@]+)"
    r"@(?P<cred_host>[^\s/@:\"'<>]+)"
)
# D-CIP-15 / BUG-228: a documented template placeholder (the repo's own
# convention -- see deploy_wizard.py's ``_warn_production_safety`` and
# meristem.observability.langfuse_trust's ``_CREDENTIAL_SENTINELS``)
# is never a live credential, so a URI shaped like one must not be flagged as
# though it were. This set had drifted out of sync with
# scripts/check_wheel_privacy.py's own ``_CREDENTIAL_PLACEHOLDER_TOKENS`` --
# the comment already claimed they mirrored each other, but that script's
# set additionally recognizes "agent" (this repo's own
# ``postgresql://agent:agent@localhost:5432/agent_kg`` documented example
# DSN, README.md / docs/architecture/graph_backends_architecture.md),
# "password", "secret", "test", and "sample" as placeholder words. Restored
# so the two gates actually agree, as documented.
_CREDENTIAL_PLACEHOLDER_TOKENS = frozenset(
    {
        "agent",
        "changeme",
        "change_me",
        "example",
        "fixme",
        "masked",
        "password",
        "placeholder",
        "redacted",
        "replace",
        "sample",
        "secret",
        "test",
        "todo",
        "xxxx",
        "your",
    }
)
_HOST_IDENTITY_RE = re.compile(r"(?i)\bssh://(?!\$\{)[^\s/@]+@")
_MACHINE_HOST_ID_RE = re.compile(r"(?i)(?<![a-z0-9-])(?:rw?|host)[0-9]{3,}(?![a-z0-9])")
_NEUTRAL_AUTHOR_NAME = "repository maintainers"
_NEUTRAL_AUTHOR_EMAIL_SUFFIX = "@example.invalid"


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    category: str
    content_hash: str
    ordinal: int

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.category}"


def _content_hash(text: str) -> str:
    """Irreversible fingerprint of a line's content, never the value itself.

    A SHA-256 digest cannot be inverted back to the sensitive substring that
    produced it, so it is safe to compute and hold in memory even though
    ``render()``/every printed message still withholds the matched value.
    """
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _is_credential_placeholder(secret: str) -> bool:
    rendered = secret.strip()
    if not rendered:
        return True
    if re.fullmatch(r"(?:\*+|#+|x{4,})", rendered, flags=re.IGNORECASE):
        return True
    tokens = set(re.findall(r"[a-z0-9]+", rendered.lower()))
    return bool(tokens & _CREDENTIAL_PLACEHOLDER_TOKENS)


def _is_credential_exempt(match: re.Match[str]) -> bool:
    """A credential-shaped URI is not a real leak when either the secret
    token is a documented placeholder word (existing behaviour) OR the host
    it targets is RFC-reserved-for-documentation (BUG-228) -- a made-up
    password pointed at ``example.test``/``localhost``/etc. cannot be a live
    credential no matter what the password portion looks like.
    """
    if _is_credential_placeholder(match.group("secret")):
        return True
    host = match.group("cred_host")
    return bool(host) and _is_reserved_hostname(host)
