"""Source-quality proofs for the desktop client (AXIL-CLIENT-R020.*).

Every test measures the repository through a helper in
``tests/support/source_quality.py`` and rejects a synthetic counterexample, so a
check that cannot fail cannot pass either. The scorer tests run the shipped
code-enhancer domain scripts as the quality gate does.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

import tests.support.source_quality as sq
from tests.support.source_quality import ROOT, SOURCE

PYPROJECT = sq.load_pyproject()
PROJECT = PYPROJECT["project"]
EXTRAS = PROJECT["optional-dependencies"]
README = (ROOT / "README.md").read_text(encoding="utf-8")
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")


# ---- dependency contract (R020.1 to R020.5) --------------------------------


@pytest.mark.spec("AXIL-CLIENT-R020.1")
def test_source_quality_1() -> None:
    for extra in ("test", "dev"):
        assert sq.declares_minimum(EXTRAS[extra], "pytest-qt", "4.5.0"), extra
        assert sq.declares_minimum(EXTRAS[extra], "pytest-timeout", "2.4.0"), extra
    assert not sq.declares_minimum(["pytest-qt>=3.0"], "pytest-qt", "4.5.0")
    assert not sq.declares_minimum(["pytest>=9"], "pytest-qt", "4.5.0")


@pytest.mark.spec("AXIL-CLIENT-R020.2")
def test_source_quality_2() -> None:
    assert sq.declares_minimum(PROJECT["dependencies"], "PySide6", "6.12.0")
    classifiers = set(PROJECT["classifiers"])
    for needed in (
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.14",
    ):
        assert needed in classifiers, needed
    assert PROJECT["requires-python"].startswith(">=3.12")
    assert not sq.declares_minimum(["PySide6"], "PySide6", "6.12.0")


@pytest.mark.spec("AXIL-CLIENT-R020.3")
def test_source_quality_3() -> None:
    deps = PROJECT["dependencies"]
    assert sq.requirement(deps, "arbora") is not None
    engine_packages = ("medulla", "meristem", "agent-utilities", "tuig", "agent-webui")
    assert [p for p in engine_packages if sq.requirement(deps, p)] == []
    assert sq.requirement(["medulla>=3"], "medulla") is not None


@pytest.mark.spec("AXIL-CLIENT-R020.4")
def test_source_quality_4() -> None:
    windows_only = [d for d in PROJECT["dependencies"] if "win32" in d]
    assert windows_only, "the Windows-only dependencies must stay declared"
    for spec in windows_only:
        req = sq.requirement([spec], spec.split(";")[0].split(">")[0].strip())
        assert req is not None and req.marker is not None
        assert req.marker.evaluate({"sys_platform": "win32"})
        assert not req.marker.evaluate({"sys_platform": "linux"})
        assert (
            sq.lower_bound(req) is not None
        ), f"{spec} needs a lower bound before its marker"
    assert (
        sq.lower_bound(sq.requirement(["pywin32; sys_platform == 'win32'"], "pywin32"))
        is None
    )


@pytest.mark.spec("AXIL-CLIENT-R020.5")
def test_source_quality_5() -> None:
    config = yaml.safe_load(
        (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    )
    black_repo = next(r for r in config["repos"] if r["repo"].endswith("/black"))
    hook_text = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    pinned = re.search(r"/black\s+rev: [0-9a-f]{40} # (\d+\.\d+\.\d+)", hook_text)
    assert pinned and black_repo["hooks"][0]["id"] == "black"
    for extra in ("test", "dev"):
        assert sq.declares_minimum(EXTRAS[extra], "black", pinned.group(1)), extra
    assert not sq.declares_minimum(["black>=1.0"], "black", pinned.group(1))


# ---- structure (R020.6, R020.7, R020.13) ------------------------------------


def _init_lines(source: str) -> int:
    tree = ast.parse(source)
    return max(
        sq.function_lines(n)
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "__init__"
    )


@pytest.mark.spec("AXIL-CLIENT-R020.6")
def test_source_quality_6() -> None:
    assert (
        _init_lines((SOURCE / "axil.py").read_text(encoding="utf-8"))
        <= sq.MAX_FUNCTION_LINES
    )
    assert (
        sq.oversized_functions((SOURCE / "axil.py").read_text(encoding="utf-8")) == []
    )
    long_body = "class A:\n    def __init__(self):\n" + "        x = 1\n" * (
        sq.MAX_FUNCTION_LINES + 5
    )
    assert _init_lines(long_body) > sq.MAX_FUNCTION_LINES


@pytest.mark.spec("AXIL-CLIENT-R020.7")
def test_source_quality_7() -> None:
    assert (
        sq.too_complex_functions((SOURCE / "axil.py").read_text(encoding="utf-8")) == []
    )
    branching = "def f(x):\n" + "".join(
        f"    if x == {i}:\n        return {i}\n" for i in range(sq.MAX_COMPLEXITY + 1)
    )
    assert sq.too_complex_functions(branching) == ["f"]


@pytest.mark.spec("AXIL-CLIENT-R020.13")
def test_source_quality_13() -> None:
    for path in sq.python_sources() + sorted((ROOT / "scripts").glob("*.py")):
        assert (
            sq.module_lines(path.read_text(encoding="utf-8")) <= sq.MAX_MODULE_LINES
        ), path
    assert sq.module_lines("x = 1\n" * (sq.MAX_MODULE_LINES + 1)) > sq.MAX_MODULE_LINES


# ---- tests (R020.8, R020.17, R020.25) ---------------------------------------


def _test_modules() -> list[Path]:
    return sorted(
        p
        for p in (ROOT / "tests").rglob("test_*.py")
        if p.name != "test_source_quality.py"
    )


@pytest.mark.spec("AXIL-CLIENT-R020.8")
def test_source_quality_8() -> None:
    total = negative = 0
    for path in _test_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and node.name.startswith("test"):
                total += 1
                negative += sq.is_negative_test(node)
    assert total >= 100
    assert (
        negative / total >= 0.25
    ), f"{negative} of {total} tests prove a refusal or failure"
    probe = ast.parse("def test_ok():\n    assert 1 == 1\n").body[0]
    assert not sq.is_negative_test(probe)
    assert sq.is_negative_test(
        ast.parse("def test_rejects_bad():\n    assert 1\n").body[0]
    )


@pytest.mark.spec("AXIL-CLIENT-R020.17")
def test_source_quality_17() -> None:
    unbound = [
        p.name
        for p in _test_modules()
        if not re.search(r"mark\.(spec|concept)\(", p.read_text(encoding="utf-8"))
    ]
    assert unbound == []


@pytest.mark.spec("AXIL-CLIENT-R020.25")
def test_source_quality_25() -> None:
    cases = [
        (p.name, n.name, sq.has_observable_assertion(n))
        for p in _test_modules()
        for n in sq.parametrized_tests(p.read_text(encoding="utf-8"))
    ]
    assert len(cases) >= 8, "repeated input cases must be parametrized"
    assert [c for c in cases if not c[2]] == []
    sample = (
        "import pytest\n@pytest.mark.parametrize('x', [1])\ndef test_a(x):\n    pass\n"
    )
    (node,) = sq.parametrized_tests(sample)
    assert not sq.has_observable_assertion(node)


# ---- documentation (R020.9 to R020.12, R020.26 to R020.28) -----------------


@pytest.mark.spec("AXIL-CLIENT-R020.9")
def test_source_quality_9() -> None:
    scripts = set(PROJECT["scripts"])
    shell = re.findall(
        r"^\s*(?:QT_QPA_PLATFORM=\S+\s+)?(?:uv run )(axil[\w-]*)", README, flags=re.M
    )
    assert shell and set(shell) <= scripts
    assert sq.main_check_passes()
    assert "axil-missing" not in scripts


@pytest.mark.spec("AXIL-CLIENT-R020.10")
def test_source_quality_10() -> None:
    for script in PROJECT["scripts"]:
        assert (
            f"`{script}`" in README
            or f"run {script}" in README
            or re.search(rf"\b{re.escape(script)}\b", README)
        ), script
    assert not re.search(r"\baxil-missing\b", README)


@pytest.mark.spec("AXIL-CLIENT-R020.11")
def test_source_quality_11() -> None:
    packages = sorted(
        p.name for p in SOURCE.iterdir() if p.is_dir() and (p / "__init__.py").exists()
    )
    assert packages
    for package in packages:
        assert f"axil/{package}" in AGENTS or f"{package}/" in AGENTS, package
    assert "axil/nonexistent" not in AGENTS


@pytest.mark.spec("AXIL-CLIENT-R020.12")
def test_source_quality_12() -> None:
    tracked = sq.tracked_files()
    pages = [
        ROOT / "README.md",
        ROOT / "AGENTS.md",
        *sorted((ROOT / "docs").glob("*.md")),
    ]
    for page in pages:
        text = page.read_text(encoding="utf-8")
        assert sq.unresolved_links(text, page.parent, tracked) == [], page
    assert sq.unresolved_links("[x](docs/does-not-exist.md)", ROOT, tracked) == [
        "docs/does-not-exist.md"
    ]


_ENV_FILES = [*sq.python_sources(), *sorted((ROOT / "scripts").glob("*.py"))]


@pytest.mark.spec("AXIL-CLIENT-R020.26")
def test_source_quality_26() -> None:
    names: set[str] = set()
    for path in _ENV_FILES:
        names |= sq.env_vars_read(path.read_text(encoding="utf-8"))
    assert names
    assert sq.missing_from_text(names, README) == []
    assert sq.missing_from_text(["AXIL_NOT_DOCUMENTED"], README) == [
        "AXIL_NOT_DOCUMENTED"
    ]


@pytest.mark.spec("AXIL-CLIENT-R020.27")
def test_source_quality_27() -> None:
    for name in ("TERM", "_MEIPASS", "_MEIPASS2", "QT_QPA_PLATFORM"):
        row = next(
            (line for line in README.splitlines() if line.startswith(f"| `{name}`")), ""
        )
        assert row, name
    term = next(line for line in README.splitlines() if line.startswith("| `TERM`"))
    meipass = next(
        line for line in README.splitlines() if line.startswith("| `_MEIPASS`")
    )
    assert "terminal" in term.lower()
    assert "bundled" in meipass.lower()


@pytest.mark.spec("AXIL-CLIENT-R020.28")
def test_source_quality_28() -> None:
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    documented = set(re.findall(r"^([A-Z_][A-Z0-9_]*)=", example, flags=re.M))
    for name in ("QT_QPA_PLATFORM", "TERM", "_MEIPASS", "AXIL_OPERATION_REGISTRY_PATH"):
        assert name in documented, name
    assert not sq.secret_assignments(example)
    assert sq.secret_assignments("GATEWAY_TOKEN=abc123\n") == ["GATEWAY_TOKEN"]


# ---- presentation / adapter seam, concepts (R020.14 to R020.16, R020.18, R020.29)


_REMOVED_GRAPH_INTERNALS = (
    "meristem",
    "agent_utilities",
    "epistemic_graph",
    "graph_os",
    "medulla",
    "arbora.gateway",
)


@pytest.mark.spec("AXIL-CLIENT-R020.14")
def test_source_quality_14() -> None:
    for path in (SOURCE / "qt").glob("*.py"):
        assert (
            sq.forbidden_imports(
                path.read_text(encoding="utf-8"), ("httpx", "ssl", "urllib")
            )
            == []
        ), path
    for path in (SOURCE / "services").glob("*.py"):
        assert (
            sq.forbidden_imports(path.read_text(encoding="utf-8"), ("PySide6",)) == []
        ), path
    assert sq.forbidden_imports(
        "import httpx\nfrom ssl import x\n", ("httpx", "ssl")
    ) == ["httpx", "ssl"]


@pytest.mark.spec("AXIL-CLIENT-R020.29")
def test_source_quality_29() -> None:
    for path in sq.python_sources() + sorted((ROOT / "scripts").glob("*.py")):
        assert (
            sq.forbidden_imports(
                path.read_text(encoding="utf-8"), _REMOVED_GRAPH_INTERNALS
            )
            == []
        ), path
    assert sq.forbidden_imports(
        "from meristem.graph import x\n", _REMOVED_GRAPH_INTERNALS
    ) == ["meristem.graph"]


_CONCEPTS = yaml.safe_load(
    (ROOT / "docs" / "concepts.yaml").read_text(encoding="utf-8")
)["concepts"]
_CONCEPT_ID = re.compile(r"\bGBOT-\d+\.\d+\b")


def _concept_ids_used(paths: list[Path], pattern: str) -> set[str]:
    used: set[str] = set()
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.search(pattern, line):
                used |= set(_CONCEPT_ID.findall(line))
    return used


@pytest.mark.spec("AXIL-CLIENT-R020.15")
def test_source_quality_15() -> None:
    registered = {str(c).split()[0] for c in _CONCEPTS}
    assert registered
    referenced = _concept_ids_used(
        sq.python_sources(), r"CONCEPT:"
    ) | _concept_ids_used(sorted((ROOT / "tests").rglob("*.py")), r"mark\.concept")
    assert registered - referenced == set()
    owners = sq.concept_owners(
        (ROOT / "docs" / "concepts.yaml").read_text(encoding="utf-8")
    )
    assert set(owners) == registered
    modules = {p.stem for p in sq.python_sources()}
    assert [c for c, module in owners.items() if module and module not in modules] == []
    assert sq.concept_owners("  - GBOT-1.0  # Gone (no_such_module)\n") == {
        "GBOT-1.0": "no_such_module"
    }
    assert "no_such_module" not in modules


@pytest.mark.spec("AXIL-CLIENT-R020.16")
def test_source_quality_16() -> None:
    registered = {str(c).split()[0] for c in _CONCEPTS}
    used = _concept_ids_used(sq.python_sources(), r"CONCEPT:") | _concept_ids_used(
        sorted((ROOT / "tests").rglob("*.py")), r"mark\.concept"
    )
    assert used - registered == set()
    assert {"GBOT-99.9"} - registered == {"GBOT-99.9"}


@pytest.mark.spec("AXIL-CLIENT-R020.18")
def test_source_quality_18() -> None:
    unnamed = []
    for path in sq.python_sources():
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and sq.function_lines(node) >= sq.SIGNIFICANT_FUNCTION_LINES
            ):
                if not sq.names_contract(node, text, ast.get_docstring(tree) or ""):
                    unnamed.append(f"{path.name}:{node.name}")
    assert unnamed == []
    code = "def big():\n" + "    x = 1\n" * 45
    node = ast.parse(code).body[0]
    assert isinstance(node, ast.FunctionDef)
    assert not sq.names_contract(node, code, "")
    assert sq.names_contract(node, code, "CONCEPT:MERISTEM-GBOT.cockpit.through-gbot")


# ---- lint, types, formatter, changelog (R020.19 to R020.24) -----------------


def _run(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout
    )


@pytest.mark.spec("AXIL-CLIENT-R020.19")
@pytest.mark.timeout(300)
def test_source_quality_19() -> None:
    clean = _run([sys.executable, "-m", "ruff", "check", "axil", "scripts", "tests"])
    assert clean.returncode == 0, clean.stdout
    dirty = ROOT / "tests" / "_ruff_probe_unused.py"
    probe = textwrap.dedent("def f():\n    import os, sys\n    return undefined_name\n")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--stdin-filename", "probe.py", "-"],
        input=probe,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0 and not dirty.exists()


@pytest.mark.spec("AXIL-CLIENT-R020.20")
@pytest.mark.timeout(600)
def test_source_quality_20() -> None:
    clean = _run([sys.executable, "-m", "mypy", "axil"], timeout=540)
    assert clean.returncode == 0, clean.stdout[-2000:]
    bad = ROOT / "tests" / "_mypy_probe.py"
    assert not bad.exists()
    probe = _run([sys.executable, "-m", "mypy", "-c", "x: int = 'a'"], timeout=120)
    assert probe.returncode != 0


@pytest.mark.spec("AXIL-CLIENT-R020.21")
def test_source_quality_21() -> None:
    text = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    pins = sq.pinned_hook_revisions(text)
    assert re.fullmatch(
        r"[0-9a-f]{40}", pins["black"]
    ), "the formatter hook must pin an immutable revision"
    unpinned = sq.pinned_hook_revisions("  - repo: https://x/black\n    rev: 26.1.0\n")
    assert not re.fullmatch(r"[0-9a-f]{40}", unpinned["black"])


@pytest.mark.spec("AXIL-CLIENT-R020.22")
def test_source_quality_22() -> None:
    import keepachangelog

    parsed = keepachangelog.to_dict(str(ROOT / "CHANGELOG.md"))
    assert parsed and PROJECT["version"] in parsed
    assert "9.9.9" not in parsed


@pytest.mark.spec("AXIL-CLIENT-R020.23")
def test_source_quality_23() -> None:
    import keepachangelog

    parsed = keepachangelog.to_dict(str(ROOT / "CHANGELOG.md"))
    entry = parsed[PROJECT["version"]]
    assert any(
        entry.get(section) for section in ("added", "changed", "fixed", "removed")
    )
    assert sq.changelog_names_rows(entry, ("AXIL-CLIENT-R019", "AXIL-CLIENT-R014"))
    assert not sq.changelog_names_rows({"added": ["unrelated"]}, ("AXIL-CLIENT-R019",))


@pytest.mark.spec("AXIL-CLIENT-R020.24")
def test_source_quality_24() -> None:
    import importlib.util

    assert sq.declares_minimum(EXTRAS["test"], "keepachangelog", "2.0.0")
    assert importlib.util.find_spec("keepachangelog") is not None
    assert not sq.declares_minimum(EXTRAS["test"], "not-a-parser", "1.0.0")
