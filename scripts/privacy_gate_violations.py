"""Per-artifact violation building and the scan entry for the privacy gate.

Walks the discovered public-text and runtime-source artifacts, classifies
every line, and accumulates :class:`privacy_gate_credentials.Violation`
records with stable ordinals (so a moved-but-identical line reports as the
same finding, not a phantom new one).
"""

from __future__ import annotations

import re
from pathlib import Path

from privacy_gate_artifacts import _runtime_source_artifacts, _tracked_artifacts
from privacy_gate_classification import (
    _is_deployment_doc,
    classify_line,
    classify_runtime_source_line,
)
from privacy_gate_credentials import (
    _NEUTRAL_AUTHOR_EMAIL_SUFFIX,
    _NEUTRAL_AUTHOR_NAME,
    Violation,
    _content_hash,
)
from privacy_gate_identity import ROOT, derive_local_identifiers


def _is_bundled_connector_profile(path: Path) -> bool:
    parts = tuple(part.casefold() for part in path.parts)
    return parts[:4] == (
        "meristem",
        "protocols",
        "source_connectors",
        "profiles",
    ) and path.suffix.casefold() in {".py", ".json", ".yaml", ".yml"}


def _is_non_neutral_author_line(folded: str, in_project_authors: bool) -> bool:
    if re.match(r"authors\s*=", folded):
        return (
            _NEUTRAL_AUTHOR_NAME not in folded
            or _NEUTRAL_AUTHOR_EMAIL_SUFFIX not in folded
        )
    if in_project_authors and re.match(r"name\s*=", folded):
        return _NEUTRAL_AUTHOR_NAME not in folded
    if in_project_authors and re.match(r"email\s*=", folded):
        return _NEUTRAL_AUTHOR_EMAIL_SUFFIX not in folded
    return False


def _author_metadata_lines(path: Path, lines: list[str]) -> list[int]:
    """Return non-neutral package-author lines without returning their values."""
    if path.suffix.casefold() != ".toml":
        return []
    violations: list[int] = []
    in_project_authors = False
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == "[[project.authors]]":
            in_project_authors = True
            continue
        if in_project_authors and stripped.startswith("["):
            in_project_authors = False
        if _is_non_neutral_author_line(stripped.casefold(), in_project_authors):
            violations.append(number)
    return violations


def _next_ordinal(
    counts: dict[tuple[str, str, str], int], group: tuple[str, str, str]
) -> int:
    ordinal = counts.get(group, 0)
    counts[group] = ordinal + 1
    return ordinal


def _tracked_artifact_violations(
    path: Path,
    root: Path,
    identifiers: frozenset[str],
    ordinals: dict[tuple[str, str, str], int],
) -> list[Violation]:
    relative = path.relative_to(root)
    rel_str = relative.as_posix()
    deployment_doc = _is_deployment_doc(relative)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    violations: list[Violation] = []
    for number in _author_metadata_lines(path, lines):
        category = "non-neutral package author identity"
        content_hash = _content_hash(lines[number - 1])
        ordinal = _next_ordinal(ordinals, (rel_str, category, content_hash))
        violations.append(Violation(rel_str, number, category, content_hash, ordinal))
    for number, line in enumerate(lines, 1):
        for category in classify_line(
            line,
            identifiers=identifiers,
            deployment_doc=deployment_doc,
        ):
            content_hash = _content_hash(line)
            ordinal = _next_ordinal(ordinals, (rel_str, category, content_hash))
            violations.append(
                Violation(rel_str, number, category, content_hash, ordinal)
            )
    return violations


def _runtime_source_violations(
    path: Path,
    root: Path,
    identifiers: frozenset[str],
    ordinals: dict[tuple[str, str, str], int],
) -> list[Violation]:
    relative = path.relative_to(root)
    rel_str = relative.as_posix()
    violations: list[Violation] = []
    if _is_bundled_connector_profile(relative):
        category = "bundled environment-specific connector profile"
        # Whole-file finding, not line-anchored: hash the path itself so
        # it stays stable regardless of the file's own line churn.
        content_hash = _content_hash(rel_str)
        ordinal = _next_ordinal(ordinals, (rel_str, category, content_hash))
        violations.append(Violation(rel_str, 1, category, content_hash, ordinal))
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for number, line in enumerate(lines, 1):
        for category in classify_runtime_source_line(line, identifiers=identifiers):
            content_hash = _content_hash(line)
            ordinal = _next_ordinal(ordinals, (rel_str, category, content_hash))
            violations.append(
                Violation(rel_str, number, category, content_hash, ordinal)
            )
    return violations


def scan(root: Path = ROOT) -> list[Violation]:
    identifiers = derive_local_identifiers(root)
    violations: list[Violation] = []
    # (path, category, content_hash) -> count so far, i.e. an ordinal
    # disambiguating two genuinely-identical lines in the same file/category —
    # never the line number, which drifts under unrelated edits and would
    # otherwise report a moved (not new) leak as a phantom NEW finding.
    ordinals: dict[tuple[str, str, str], int] = {}
    for path in _tracked_artifacts(root):
        if path.is_file():
            violations.extend(
                _tracked_artifact_violations(path, root, identifiers, ordinals)
            )
    for path in _runtime_source_artifacts(root):
        if path.is_file():
            violations.extend(
                _runtime_source_violations(path, root, identifiers, ordinals)
            )
    return violations
