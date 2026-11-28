"""AXIL-CLIENT-R021 (PIPE-GATES-R086.8): this repository runs the shared state-machine census in staged mode.

The census is adopted in mode ``staged`` (findings are printed, the hook exits 0)
until the last state-machine row of this repository is verified. The shared hook
itself is tested in pipelines.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.spec("AXIL-CLIENT-R021")
def test_census_policy_declares_existing_paths() -> None:
    table = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["pipelines_hooks"][
        "state_machine"
    ]
    assert table["mode"] == "staged"
    assert table["paths"] and all((ROOT / path).is_dir() for path in table["paths"])
    assert table["languages"] and set(table["languages"]) <= {"python", "rust"}
