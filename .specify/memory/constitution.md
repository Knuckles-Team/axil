# Axil constitution

This repository inherits the [organization constitution](https://github.com/Knuckles-Team/pipelines/blob/main/.specify/memory/constitution.md) version 1.0.0. Every article of that constitution applies here. This file adds only the rules and limits of this repository.

**Inherits**: organization constitution v1.0.0 | **Version**: 1.0.0 | **Ratified**: 2026-10-31 | **Last amended**: 2026-10-31

## Organization standards

- [Spec standard](https://github.com/Knuckles-Team/pipelines/blob/main/reference/spec-standard.md): one owning spec per capability, computed states, `Spec:` trailers.
- [Ecosystem boundaries](https://github.com/Knuckles-Team/pipelines/blob/main/reference/ecosystem-boundaries.md): which repository owns which requirement.
- [Wording standard](https://github.com/Knuckles-Team/pipelines/blob/main/reference/ste.md): sentences of 20 words or fewer, with `must`, `should`, or `may`.

## Repository articles

### R-I. The desktop and chat client presents; arbora decides

Axil shows data and takes input in the desktop and chat client. It reads data only through the arbora client and imports no engine, harness or other interface package.

**Enforced by:** Pre-commit hook `coupling` (`--root .`); [ecosystem boundaries](https://github.com/Knuckles-Team/pipelines/blob/main/reference/ecosystem-boundaries.md), axil row and forbidden-import matrix.

**Plan check:** Does every data access in the change go through the arbora client?

### R-II. Source merges run the mandatory tests

A change that merges source runs the full test suite against the current default branch, outside the gateway scope.

**Enforced by:** Pre-commit hook `source-merge-tests` (`scripts/check_source_merge.py`).

**Plan check:** Do the full tests pass against the current default branch?

### R-III. Tracked artifacts carry no host data or local identity

Tracked public artifacts hold no host-specific data and no local identity.

**Enforced by:** Pre-commit hook `guardrail-tracked-privacy` (`scripts/check_tracked_privacy.py`) and the organization `tracked-privacy` gate.

**Plan check:** Do the new tracked files hold only portable, neutral text?

## Repository limits

This repository sets no numeric limit of its own. It follows the organization limits table.

Amend this file in a reviewed change. State the impact in the pull request. When the organization constitution changes its version, update the **Inherits** line in the same change.
