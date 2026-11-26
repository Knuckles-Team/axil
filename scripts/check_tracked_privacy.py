#!/usr/bin/env python3
"""Reject host-specific data and local identities from tracked public artifacts.

Identifiers are derived in memory from the current account, home, checkout and
host. Findings report only ``file:line`` and a category; the sensitive matched
value is never written or printed. Machine paths and persisted path fields are
checked independently, so the gate remains useful in clean CI environments.

Ported verbatim from meristem's ``scripts/check_tracked_privacy.py``
(guardrail-tracked-privacy), which already passes green on meristem's
own ``main`` -- reused rather than reinvented per this fleet's
Extend-Before-Invent convention (near-duplicate gate helpers have drifted
apart before; see MEMORY ``gate-tool-published-before-gate-adopted``). The
ONLY behavioral change from the meristem original is
``privacy_gate_artifacts._is_runtime_source_path``, which no longer gates on
meristem's OWN top-level directory allowlist (``meristem``,
``deploy``, ``docker``, ...) -- that allowlist is specific to that repo's
tree shape, and porting it unmodified into a repo with a different tree
(e.g. this repo's own top-level source directories) would silently scan an
EMPTY universe for every directory not on the borrowed list: a confident
green verdict over zero files, the exact "gates that report more coverage
than they have" failure this fleet has hit before. See that function's own
docstring for the replacement rule.

The gate's logic is split across the ``privacy_gate_*`` modules next to
this entry point: home-path patterns (``privacy_gate_home_paths``),
reserved hostnames (``privacy_gate_hostnames``), persisted-path and
endpoint patterns (``privacy_gate_patterns``), credentials and the
Violation model (``privacy_gate_credentials``), identifier derivation
(``privacy_gate_identity``), line classification
(``privacy_gate_classification``), artifact discovery
(``privacy_gate_artifacts``), and violation building (``privacy_gate_violations``).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _git_subprocess_env import strip_inherited_git_repository_env  # noqa: E402
from privacy_gate_classification import (  # noqa: E402
    classify_line,
    classify_runtime_source_line,
)
from privacy_gate_credentials import Violation  # noqa: E402
from privacy_gate_identity import derive_local_identifiers  # noqa: E402
from privacy_gate_violations import scan  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# NE-059 (sibling of BUG-180/D-LGI-1): strip the git-repository-redirecting
# env vars process-wide before anything in this gate shells out to git;
# each git-shelling module re-asserts the strip at its own import time, so
# importing a privacy_gate_* module directly stays safe too.
strip_inherited_git_repository_env()


# CX-RAT-09 (2026-08-27): the baseline/ratchet mechanism (frozen
# ``tracked_privacy_baseline.txt``, ``--update-baseline``) is DELETED, not
# merely emptied. A count-based allowance is the wrong instrument for a
# leak-prevention gate on a repo that publishes to a PUBLIC GitHub org: "N
# leaks are acceptable" is not a defensible end state at any N, and a count
# lets a NEW hostname leak hide behind a pre-existing FIXED one (fixing one
# baselined entry "spends" the budget a genuinely new leak could then use
# without tripping the gate). All findings visible at conversion time were
# burned to zero in the same commit as this rewrite -- see MEMORY
# ``no-ratchets-expose-tech-debt``: baseline/ratchet gates are not allowed in
# this workspace; findings are debt to burn down, never to freeze behind an
# allowance. ``MAX`` is an ABSOLUTE constant (not a per-repo drift budget)
# enforced regardless of how this script is invoked -- some callers in this
# fleet run gates through a zero-argument glob runner that never passes a
# ``--max`` flag, so the threshold lives in code, not in an argument a caller
# could omit.
MAX = 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="check-tracked-privacy")
    parser.parse_args()

    violations = scan()
    count = len(violations)
    # Printed unconditionally -- pass or fail -- so the real count is always
    # visible in CI/pre-commit output, never only on failure.
    print(f"Tracked artifact privacy gate: {count} finding(s) (MAX={MAX}).")

    if count > MAX:
        print("Tracked artifact privacy gate FAILED:")
        for violation in violations:
            print(f"  - {violation.render()}")
        print("Matched values are intentionally suppressed.")
        print(f"{count} leak(s) found; absolute maximum is {MAX}.")
        # D-ORC-53: this gate returned a DIFFERENT verdict for the SAME tree
        # depending on invocation method (standalone script vs. via
        # pre-commit) at least once, with no code change in between — a
        # non-reproducible privacy verdict trains people to skip a gate that
        # is right often enough to be dangerous when it is silent. Printing
        # exactly what was resolved turns the NEXT occurrence into evidence
        # instead of another "prove it happened after the fact" investigation.
        print(
            "resolution (D-ORC-53 forensic breadcrumb): "
            f"ROOT={ROOT} cwd={Path.cwd()} total_violations={count} "
            f"PRE_COMMIT_HOME={os.environ.get('PRE_COMMIT_HOME', '<unset>')!r}"
        )
        return 1
    print("Tracked artifact privacy gate PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
