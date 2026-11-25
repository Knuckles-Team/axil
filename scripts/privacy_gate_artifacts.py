"""Tracked-artifact discovery for the tracked-privacy gate.

Chooses the file universe the gate scans: the public text-artifact pass and
the runtime-source pass, both preferring git's own tracked file set and
falling back to a bounded filesystem walk in no-Git snapshots.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _git_subprocess_env import (
    sanitized_git_env,
    strip_inherited_git_repository_env,
)  # noqa: E402
from privacy_gate_home_paths import _SOURCE_SUFFIXES, _TEXT_SUFFIXES  # noqa: E402

# NE-059 (sibling of BUG-180/D-LGI-1): the ``git ls-files`` call below can
# inherit a real ``git commit``/``git push``'s exported
# ``GIT_DIR``/``GIT_INDEX_FILE`` unmodified when this script runs as its own
# pre-commit hook; those vars win over ``cwd=``'s path-based repository
# discovery. As a *privacy/security* gate, a poisoned resolution is worse
# than a crash -- it can silently swap in a different repository's
# tracked-file inventory or let a decoy's exclude rules drop a real leaking
# file from the sweep, so the gate reports PASS having never looked at the
# file that leaks. Strip once, process-wide, at import time *and* pass an
# explicit sanitized ``env=`` at each call site.
strip_inherited_git_repository_env()

_SCAN_EXCLUDED_DIRECTORIES = frozenset(
    {
        ".acp-sessions",
        ".benchmarks",
        ".git",
        ".hypothesis",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".pytest_tmp",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
        "node_modules",
        "site",
        "target",
        "venv",
        "workspace",
    }
)
_MAX_SCAN_FILES = 500_000

# BUG-228: this used to be {"docs", ".github"} plus top-level files and any
# *.toml, which is why a leak that landed under `tests/` or `.specify/` was
# structurally invisible to this pass -- the gate's own selection excluded
# the tree, not the file type. A tracked test fixture in a PUBLIC repo
# discloses exactly as much as tracked source: the file's location was never
# a legitimate signal for whether its content is safe to publish. Widened to
# every tracked-but-previously-excluded text tree that can carry a fixture
# (tests/), a design/spec artifact (.specify/), or a runnable example
# (examples/) -- not just the two trees someone happened to think of first.
_PUBLIC_TEXT_TREES = frozenset({"docs", ".github", "tests", ".specify", "examples"})


def _is_public_artifact(name: str) -> bool:
    path = Path(name)
    if path.suffix.casefold() not in _TEXT_SUFFIXES:
        return False
    if "skills" in path.parts:
        return False
    return (
        path.parts[0] in _PUBLIC_TEXT_TREES
        or len(path.parts) == 1
        or path.suffix.casefold() == ".toml"
    )


def _is_traversable_dir(current: Path, name: str) -> bool:
    if name in _SCAN_EXCLUDED_DIRECTORIES or name.endswith(".egg-info"):
        return False
    metadata = (current / name).lstat()
    if stat.S_ISLNK(metadata.st_mode):
        return False
    return stat.S_ISDIR(metadata.st_mode)


def _regular_files_in(current: Path, file_names) -> list[Path]:
    found: list[Path] = []
    for name in sorted(file_names):
        path = current / name
        metadata = path.lstat()
        if stat.S_ISREG(metadata.st_mode):
            found.append(path)
    return found


def _filesystem_files(root: Path) -> list[Path]:
    """Enumerate a bounded no-Git source snapshot without following links."""
    files: list[Path] = []
    for directory, directory_names, file_names in os.walk(root, topdown=True):
        current = Path(directory)
        directory_names[:] = [
            name
            for name in sorted(directory_names)
            if _is_traversable_dir(current, name)
        ]
        for path in _regular_files_in(current, file_names):
            files.append(path)
            if len(files) > _MAX_SCAN_FILES:
                raise RuntimeError("privacy source inventory exceeds its file bound")
    return files


def _git_file_names(root: Path, command: list[str]) -> list[str] | None:
    """Return Git inventory names, or ``None`` for an immutable no-Git snapshot."""
    if not (root / ".git").exists():
        return None
    result = subprocess.run(
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        env=sanitized_git_env(),
    )
    if result.returncode != 0:
        return None
    return [name for name in result.stdout.splitlines() if name]


def _tracked_artifacts(root: Path) -> list[Path]:
    names = _git_file_names(
        root,
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
    )
    candidates = (
        _filesystem_files(root) if names is None else [root / name for name in names]
    )
    return [
        path
        for path in candidates
        if _is_public_artifact(path.relative_to(root).as_posix())
    ]


def _is_runtime_source_path(path: Path) -> bool:
    """Scope the source-literal pass to every tree that can carry a real leak.

    PORT NOTE (this file is ported from meristem's identically-named
    function -- see the module docstring of ``check_tracked_privacy.py``):
    the upstream version gates this pass on meristem's OWN top-level
    directory allowlist (``meristem``, ``deploy``, ``docker``, ``helm``,
    ``k8s``, ``tests``, ``.security``, ``.specify``, ``examples``). That
    allowlist encodes ONE repo's tree shape; reusing it unmodified here
    would scope this pass to directories that mostly do not exist in THIS
    repo, so it would measure an empty (or near-empty) universe and pass
    green while scanning nothing -- exactly the "gate reports more coverage
    than it has" failure class this fleet has hit before (a hook silently
    discovering zero files). Upstream's own BUG-228 history argues against
    a location-based filter on the merits too: "a tracked test fixture in
    a PUBLIC repo discloses exactly as much as tracked source; the file's
    location was never a legitimate signal for whether its content is safe
    to publish." So this port drops the allowlist and scopes purely by
    suffix (``_SOURCE_SUFFIXES``, applied by the caller) plus git's own
    tracked/exclude-standard file set -- a directory that is gitignored
    (build output, ``node_modules``, ``target``, a virtualenv, ...) is
    already invisible to ``git ls-files --cached --others
    --exclude-standard`` and never reaches this function at all, so
    widening this check costs nothing and closes the coverage gap the
    borrowed allowlist would otherwise leave silently open.
    """
    return bool(path.parts)


def _runtime_source_artifacts(root: Path) -> list[Path]:
    """Every **tracked** runtime/deployment source path, not merely the changed ones.

    D-CIP-10. This pass used to be scoped to ``git diff``/untracked files,
    which made the gate structurally blind to its own back-catalogue: a
    machine path that landed in an earlier commit was never re-examined, so
    it stayed public forever. Combined with :func:`_is_public_artifact`'s
    *location* filter — which admits only ``docs/``, ``.github/``,
    top-level and ``*.toml`` — the two passes left a hole exactly where the
    real leaks live. ``docker/*.yaml`` passes the suffix test and fails the
    location test, so nothing scanned it; the gate reported 7 lines in 2
    ``docs/`` files while 11 tracked files carried machine paths, two of
    them a **personal** account name (D-PCC-1).

    Scanning the whole tracked tree here closes that hole without inventing
    a heuristic: the classification (:func:`classify_changed_source_line`)
    and the scope (:func:`_is_runtime_source_path`, which already lists
    ``docker``) were both already correct and already noise-tuned. Only the
    *diff* restriction was wrong.

    A public GitHub repository publishes its history, not just its tip, so
    "changed in this commit" was never the right boundary for a privacy
    gate.
    """
    names = _git_file_names(
        root,
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
    )
    candidates = (
        _filesystem_files(root) if names is None else [root / name for name in names]
    )
    return sorted(
        (
            path
            for path in candidates
            if path.suffix.casefold() in _SOURCE_SUFFIXES
            and _is_runtime_source_path(path.relative_to(root))
        ),
        key=lambda path: path.as_posix(),
    )
