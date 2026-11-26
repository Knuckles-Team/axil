"""Scored source-quality and installed-entry proofs (AXIL-CLIENT-R020.30 to R020.41).

Each scored test runs the shipped code-enhancer domain script as the quality gate
does and compares its score with the row threshold. The entry tests inspect the
installed command and launch it against a served gateway fixture.
"""

from __future__ import annotations

import ast
import os

import pytest

import tests.support.source_quality as sq
from tests.support.source_quality import ROOT, SOURCE

PROJECT = sq.load_pyproject()["project"]

_nested = pytest.mark.skipif(
    bool(os.environ.get(sq.NESTED_ENV)),
    reason="the scorer runs this suite itself; measuring it again would recurse",
)


def _run(cmd: list[str]):
    import subprocess

    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)


# ---- scorer domains (R020.30 to R020.39) -----------------------------------

_DOMAIN_FOR_ROW = {
    30: "pytest_quality",
    31: "architecture",
    32: "concepts",
    33: "tests",
    34: "changelog",
    35: "env_vars",
    36: "xdg",
}
_REPORTS: dict[str, dict] = {}


def _report(domain: str) -> dict:
    if domain not in _REPORTS:
        _REPORTS[domain] = sq.run_domain(domain)
    return _REPORTS[domain]


def _check_domain(domain: str) -> None:
    report = _report(domain)
    assert sq.score_passes(report, 80), report.get("findings")
    assert not sq.score_passes({"score": 79}, 80)


@_nested
@pytest.mark.timeout(600)
@pytest.mark.spec("AXIL-CLIENT-R020.30")
def test_source_quality_30() -> None:
    _check_domain("pytest_quality")


@_nested
@pytest.mark.timeout(600)
@pytest.mark.spec("AXIL-CLIENT-R020.31")
def test_source_quality_31() -> None:
    _check_domain("architecture")


@_nested
@pytest.mark.timeout(600)
@pytest.mark.spec("AXIL-CLIENT-R020.32")
def test_source_quality_32() -> None:
    _check_domain("concepts")


@_nested
@pytest.mark.timeout(900)
@pytest.mark.spec("AXIL-CLIENT-R020.33")
def test_source_quality_33() -> None:
    _check_domain("tests")


@_nested
@pytest.mark.timeout(600)
@pytest.mark.spec("AXIL-CLIENT-R020.34")
def test_source_quality_34() -> None:
    _check_domain("changelog")


@_nested
@pytest.mark.timeout(600)
@pytest.mark.spec("AXIL-CLIENT-R020.35")
def test_source_quality_35() -> None:
    _check_domain("env_vars")


@_nested
@pytest.mark.timeout(600)
@pytest.mark.spec("AXIL-CLIENT-R020.36")
def test_source_quality_36() -> None:
    _check_domain("xdg")


@_nested
@pytest.mark.timeout(900)
@pytest.mark.spec("AXIL-CLIENT-R020.38")
def test_source_quality_38() -> None:
    grades = {d: _report(d)["grade"] for d in sq.DOMAIN_SCRIPTS if d != "xdg"}
    assert sq.grade_floor(grades) == {}
    assert sq.grade_floor({"x": "C"}) == {"x": "C"}


@_nested
@pytest.mark.timeout(900)
@pytest.mark.spec("AXIL-CLIENT-R020.37")
def test_source_quality_37() -> None:
    grades = [_report(d)["grade"] for d in sq.DOMAIN_SCRIPTS if d != "xdg"]
    assert sq.gpa(grades) >= 3.0
    assert sq.gpa(["C", "D", "C"]) < 3.0


@_nested
@pytest.mark.timeout(900)
@pytest.mark.spec("AXIL-CLIENT-R020.39")
def test_source_quality_39() -> None:
    for domain in ("linters", "security", "changelog", "env_vars", "documentation"):
        report = _report(domain)
        assert report["score"] == 100, (domain, report.get("findings"))
    assert sq.score_passes({"score": 99}, 100) is False


# ---- installed entry (R020.40, R020.41) ------------------------------------


@pytest.mark.spec("AXIL-CLIENT-R020.40")
def test_source_quality_entry_wiring() -> None:
    assert PROJECT["scripts"]["axil"] == "axil.axil:main"
    tree = ast.parse((SOURCE / "axil.py").read_text(encoding="utf-8"))
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert {"main", "axil"} <= functions.keys()
    assert sq.calls(functions["main"], "axil")
    assert sq.calls(functions["axil"], "Axil")
    assert not sq.calls(functions["main"], "NoSuchEntry")
    out = _run(["git", "grep", "-n", "def main", "--", "axil/axil.py"])
    assert out.returncode == 0


@pytest.mark.spec("AXIL-CLIENT-R020.41")
@pytest.mark.timeout(120)
def test_source_quality_served_entry() -> None:
    denied = sq.served_entry_probe(authorized=False)
    empty = sq.served_entry_probe(authorized=True)
    assert denied["entry"] == "launched" and empty["entry"] == "launched"
    assert denied["view"] == "unavailable"
    assert empty["view"] == "empty"
    assert denied["view"] != empty["view"]
