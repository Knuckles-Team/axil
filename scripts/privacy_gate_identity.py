"""Local identifier derivation for the tracked-privacy gate.

Derives the in-memory identifier set (current account, hostname, home, and
the calling process's git identity) the gate treats as sensitive.
``AGENT_UTILITIES_PRIVACY_IDENTIFIERS`` is a declared, stable override that
pins a deterministic identity set for CI/pre-commit.
"""

from __future__ import annotations

import getpass
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

# R-07: `pwd` is POSIX-only and raises ImportError at import time on Windows.
# It only ever supplies one extra candidate identifier (the passwd-db
# username) alongside several already-portable ones (getpass.getuser(),
# hostname, env vars, home-dir name) below, so on Windows this module simply
# runs with one fewer redundant source instead of failing to import at all.
if sys.platform != "win32":
    import pwd
else:  # pragma: no cover - exercised only on Windows
    pwd = None  # type: ignore[assignment]

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _git_subprocess_env import (
    sanitized_git_env,
    strip_inherited_git_repository_env,
)  # noqa: E402
from privacy_gate_home_paths import _GENERIC_IDENTIFIERS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# NE-059 (sibling of BUG-180/D-LGI-1, ported from meristem's own fix):
# every ``git`` subprocess this module shells out to -- ``derive_local_
# identifiers``'s ``git rev-parse --git-common-dir``/``git config --get
# user.name|email`` -- can inherit a real ``git commit``/``git push``'s
# exported ``GIT_DIR``/``GIT_INDEX_FILE`` unmodified when this script runs
# as its own pre-commit hook: neither call passed its own ``env=``, and
# those vars win over ``cwd=``'s path-based repository discovery. As a
# *privacy/security* gate, a poisoned resolution is worse than a crash -- it
# can silently swap in a different repository's tracked-file inventory, so
# the gate reports PASS having never looked at the file that leaks. Strip
# once, process-wide, at import time *and* pass an explicit sanitized
# ``env=`` at each call site, so no future call in this module can regress
# silently by omitting the strip precondition.
strip_inherited_git_repository_env()


def _identifier_from_path(value: str) -> set[str]:
    identifiers: set[str] = set()
    normalized = value.replace("\\", "/")
    for pattern in (r"/home/([^/]+)", r"/Users/([^/]+)"):
        identifiers.update(re.findall(pattern, normalized, flags=re.IGNORECASE))
    return identifiers


# D-ORC-57: purely ambient derivation (OS username, hostname, the CALLING
# process's local git config) makes the verdict depend on who/where the
# scan runs, not on the tree being scanned -- the same tree can PASS
# standalone and FAIL under pre-commit for no reason other than the two
# invocations seeing different ambient identities. Observed live: a lane's
# throwaway sandbox had ``git config user.name`` set to "Guard Test" (an
# isolated test identity, unrelated to this repository), and "guard test"
# then substring-matched the unrelated phrase "architecture guard test"
# already present in a tracked comment -- 279 manufactured false leaks from
# one ambient identity accident.
#
# ``AGENT_UTILITIES_PRIVACY_IDENTIFIERS`` is a DECLARED, stable override:
# when set (comma- or newline-separated), it is used INSTEAD of the
# ambient OS/git-config-derived candidates below, so CI/pre-commit can pin
# one deterministic identity set regardless of which sandbox or host runs
# the scan. Unset, behaviour is unchanged from before this fix -- additive
# only, so a caller that has not opted in loses no coverage (the real
# absolute-homelab-path leak D-GDI-1 caught stays caught either way; that
# detector is independent of this identifier set).
#
# ``git log -1 --format=%an%n%ae`` (HEAD's own committer identity) is
# deliberately NOT one of the candidate sources below -- it was removed
# 2026-08-17 after it produced a ~450-line-across-~180-file false-positive
# flood, the same D-ORC-57 shape (a wrong ambient value substring-matching
# ordinary prose) but from a different source. ``git config user.name``/
# ``user.email`` capture the CALLING PROCESS's own stable, deliberately-set
# identity -- what this docstring means by "the current account". HEAD's
# last-commit author is not that: it is whichever identity committed most
# recently, which in this repo's own multi-agent-authored history rotates
# per commit and is, at the moment this was fixed, literally the single
# word "claude" (``git log -1 --format=%an`` on `main`) -- an ordinary,
# extremely common word in a Claude-focused agent-framework codebase, so
# every doc/comment/design-note that so much as names the tool became a
# manufactured leak. Unlike the "Guard Test" incident, adding it to
# ``_GENERIC_IDENTIFIERS`` would not fix this class -- the next commit's
# author could use another tool or model name, each requiring its own
# reactive exclusion. ``git config``'s two sources remain and already
# capture the real, stable developer identity (proven: this checkout's
# ``user.name``/``user.email`` resolve to a real name + email, independent
# of whatever authored HEAD), so removing the HEAD-author fallback loses no
# genuine detection here -- it only removes a signal that was never "the
# current account" in the first place.
def derive_local_identifiers(root: Path = ROOT) -> frozenset[str]:
    """Derive the identifier set this gate treats as sensitive in tracked text."""
    override = os.environ.get("AGENT_UTILITIES_PRIVACY_IDENTIFIERS", "").strip()
    if override:
        declared = {
            value.strip() for value in re.split(r"[,\n]", override) if value.strip()
        }
        return _filter_identifiers(declared)

    candidates = _ambient_identifier_candidates()
    candidates.update(_git_common_dir_identifiers(root))
    candidates.update(_git_config_identifiers(root))
    return _filter_identifiers(candidates)


def _filter_identifiers(candidates) -> frozenset[str]:
    return frozenset(
        value.casefold()
        for value in candidates
        if value and len(value) >= 4 and value.casefold() not in _GENERIC_IDENTIFIERS
    )


def _ambient_identifier_candidates() -> set[str]:
    """OS username, hostname (bare and short-form), user/login env vars, and
    the home directory's own name/path -- the non-Git ambient candidates."""
    candidates = {
        getpass.getuser(),
        socket.gethostname(),
        socket.gethostname().split(".", 1)[0],
        os.environ.get("USER", ""),
        os.environ.get("LOGNAME", ""),
        os.environ.get("USERNAME", ""),
        Path.home().name,
    }
    if pwd is not None:  # POSIX: one more redundant source, see import above
        candidates.add(pwd.getpwuid(os.getuid()).pw_name)
    candidates.update(_identifier_from_path(str(Path.home())))
    return candidates


def _git_common_dir_identifiers(root: Path) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            env=sanitized_git_env(),
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    return _identifier_from_path(result.stdout.strip())


def _git_config_identifiers(root: Path) -> set[str]:
    candidates: set[str] = set()
    for command in (
        ["git", "config", "--get", "user.name"],
        ["git", "config", "--get", "user.email"],
    ):
        try:
            result = subprocess.run(
                command,
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                env=sanitized_git_env(),
            )
        except OSError:
            continue
        for value in result.stdout.splitlines():
            candidates.add(value.strip())
    return candidates
