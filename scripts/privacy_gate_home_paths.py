"""Home-path and identifier-vocabulary patterns for the tracked-privacy gate.

The home-path matcher, the reserved placeholder-account vocabulary, and the
text/source suffix sets the gate's artifact discovery uses. The gate entry
point is ``scripts/check_tracked_privacy.py``; this module only carries the
patterns it scans with.
"""

from __future__ import annotations

import re

_TEXT_SUFFIXES = frozenset({".md", ".json", ".yaml", ".yml", ".toml"})
_SOURCE_SUFFIXES = frozenset(
    {".js", ".md", ".ps1", ".py", ".rs", ".sh", ".ts", ".yaml", ".yml"}
)
_GENERIC_IDENTIFIERS = frozenset(
    {
        "admin",
        "agent",
        "apps",
        "build",
        "developer",
        "genius",
        "home",
        "localhost",
        "maintainer",
        "maintainers",
        "root",
        "runner",
        "service",
        "user",
        "workspace",
    }
)
_HOME_PATH_PATTERN = (
    r"(?:(?<![A-Za-z0-9_.-])/home/(?P<home_user>[A-Za-z0-9_.-]+)(?:/|\b)|"
    r"(?<![A-Za-z0-9_.-])/Users/(?P<users_user>[A-Za-z0-9_.-]+)(?:/|\b)|"
    r"(?<![A-Za-z0-9_.-])/mnt/[A-Za-z]/Users/(?P<mnt_user>[A-Za-z0-9_.-]+)(?:/|\b)|"
    # BUG-228: this branch had no left boundary guard (unlike the three
    # above), so a REST route id like ``"route:GET:/users/{id}"`` spuriously
    # matched it -- the "T" ending "GET" read as a fake drive letter. The
    # same lookbehind the other branches already use fixes it: a real drive
    # letter is never itself preceded by another identifier character.
    r"(?<![A-Za-z0-9_.-])[A-Za-z]:[\\/]Users[\\/](?P<win_user>[^\\/\s]+)(?:[\\/]|\b))"
)
_HOME_PATH_RE = re.compile(_HOME_PATH_PATTERN, re.IGNORECASE)
# BUG-228: usernames this repo's own tests use, over and over, as a
# documented "this is not a real account" stand-in -- generic role nouns
# (operator/user/local/app/account/person), the RFC 2606 "example" word and
# its natural variants (example/example-user/exampleuser), classic
# protocol-documentation personas (alice/bob, same convention IETF RFCs
# use), this repo's own synthetic-account naming idiom (agent-user and
# other ``*-account`` fixtures), and single-letter stand-ins (a/u). None of
# these can identify a real person or host; only the ambient candidates
# :func:`privacy_gate_identity.derive_local_identifiers` derives (the
# actual current account) and a handful of specific real names (e.g. the
# developer account, the real workspace root) do that, and those are NOT in
# this set on purpose.
#
# D-W12-AU-EXCEPTIONS-3: "someone" was in this set from BUG-228 through
# 2026-08-16 but was never actually named in this comment's own rationale
# above (it does not fit "generic role noun", the "example" family, the
# alice/bob personas, the ``*-account``/agent-user idiom, or a single-letter
# stand-in) -- a stray addition, not a documented convention. It silently
# regressed tests/gates/test_docs_contract_gate.py's
# ``test_privacy_gate_scans_unchanged_runtime_source_not_only_the_diff``,
# whose fixture (``/home/`` + the placeholder account ``someone`` +
# ``/state/tree``) exists specifically to prove
# ``classify_runtime_source_line`` detects an arbitrary, non-reserved home
# path -- reserving that exact username made the positive fixture invisible,
# the same "verdict narrower than its name" failure mode BUG-241 named. A
# repo-wide sweep at fix time found zero remaining sites depending on the
# reservation, so removing it does not reopen BUG-228's ~130-false-positive
# flood; if a genuine placeholder-account home-path fixture is ever needed
# again, use one of the ALREADY-reserved words above instead of re-adding
# this one.
_RESERVED_HOME_USERS = frozenset(
    {
        "a",
        "a-different-account",
        "account",
        "agent-user",
        "alice",
        "app",
        "bob",
        "example",
        "example-user",
        "exampleuser",
        "local",
        "local-account",
        "operator",
        "person",
        "sensitive-account",
        "some-account",
        "u",
        "user",
    }
)


def _home_path_user(match: re.Match[str]) -> str | None:
    for name in ("home_user", "users_user", "mnt_user", "win_user"):
        value = match.groupdict().get(name)
        if value:
            return value
    return None


def _is_reserved_home_user(user: str) -> bool:
    return user.strip("\\/").casefold() in _RESERVED_HOME_USERS


def _has_real_home_path(line: str) -> bool:
    """True if any home-path match on this line is NOT a reserved placeholder.

    A line can carry more than one match (e.g. a before/after pair); it is
    only a real leak if at least one of them is not a documented stand-in.
    """
    return any(
        not _is_reserved_home_user(user)
        for match in _HOME_PATH_RE.finditer(line)
        for user in (_home_path_user(match),)
        if user is not None
    )
