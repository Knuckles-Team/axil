"""Measurement helpers for the source-quality rows (AXIL-CLIENT-R020).

Each helper takes the thing it measures as an argument, so a test can prove the
repository passes and a synthetic counterexample fails.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path

from packaging.requirements import Requirement
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "axil"

MAX_FUNCTION_LINES = 60
MAX_COMPLEXITY = 10
MAX_MODULE_LINES = 900
SIGNIFICANT_FUNCTION_LINES = 40

_BRANCH_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.ExceptHandler,
    ast.IfExp,
    ast.Assert,
    ast.comprehension,
)

GRADE_POINTS = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}


def load_pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def python_sources(base: Path = SOURCE) -> list[Path]:
    return sorted(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)


def requirement(specs: Iterable[str], name: str) -> Requirement | None:
    """Return the requirement named ``name`` from dependency strings, or None."""
    wanted = name.lower().replace("_", "-")
    for spec in specs:
        req = Requirement(spec)
        if req.name.lower().replace("_", "-") == wanted:
            return req
    return None


def lower_bound(req: Requirement | None) -> Version | None:
    """The lowest version a requirement admits, or None when it has no lower bound."""
    if req is None:
        return None
    bounds = [
        Version(s.version)
        for s in req.specifier
        if s.operator in (">=", "==", "~=", ">")
    ]
    return max(bounds) if bounds else None


def declares_minimum(specs: Iterable[str], name: str, minimum: str) -> bool:
    bound = lower_bound(requirement(specs, name))
    return bound is not None and bound >= Version(minimum)


def _function_nodes(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def function_lines(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return (node.end_lineno or node.lineno) - node.lineno + 1


def complexity(node: ast.AST) -> int:
    """Cyclomatic complexity: one plus the decision points inside the function."""
    total = 1
    for child in ast.walk(node):
        if isinstance(child, _BRANCH_NODES):
            total += 1
        elif isinstance(child, ast.BoolOp):
            total += len(child.values) - 1
    return total


def oversized_functions(source: str, limit: int = MAX_FUNCTION_LINES) -> list[str]:
    return [
        n.name for n in _function_nodes(ast.parse(source)) if function_lines(n) > limit
    ]


def too_complex_functions(source: str, limit: int = MAX_COMPLEXITY) -> list[str]:
    return [n.name for n in _function_nodes(ast.parse(source)) if complexity(n) > limit]


def module_lines(source: str) -> int:
    return sum(1 for line in source.splitlines() if line.strip())


def imported_modules(source: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


def forbidden_imports(source: str, prefixes: Iterable[str]) -> list[str]:
    """Imported modules that are, or sit under, one of the forbidden package names."""
    banned = tuple(prefixes)
    return sorted(
        m
        for m in imported_modules(source)
        if any(m == p or m.startswith(p + ".") for p in banned)
    )


def parametrized_tests(source: str) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Test functions that carry a ``parametrize`` decorator."""
    found = []
    for node in _function_nodes(ast.parse(source)):
        if not node.name.startswith("test"):
            continue
        for dec in node.decorator_list:
            if "parametrize" in ast.unparse(dec):
                found.append(node)
                break
    return found


def has_observable_assertion(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Assert):
            return True
        if isinstance(child, ast.With) and any(
            "raises" in ast.unparse(i.context_expr) for i in child.items
        ):
            return True
    return False


_NEGATIVE_WORDS = (
    "reject",
    "refuse",
    "fail",
    "unavailable",
    "offline",
    "denied",
    "error",
    "never",
    "not_",
    "missing",
    "invalid",
    "malformed",
    "unsafe",
    "distinct",
    "survives",
)


def is_negative_test(node: ast.AST) -> bool:
    """True when a test proves a refusal, failure or unavailable path."""
    name = getattr(node, "name", "")
    if any(word in name for word in _NEGATIVE_WORDS):
        return True
    return any(
        isinstance(c, ast.With)
        and any("raises" in ast.unparse(i.context_expr) for i in c.items)
        for c in ast.walk(node)
    )


def covers_negative_behavior(source: str) -> bool:
    """True when a test module proves a refusal, failure or unavailable path."""
    tree = ast.parse(source)
    for node in _function_nodes(tree):
        if not node.name.startswith("test"):
            continue
        if any(word in node.name for word in _NEGATIVE_WORDS):
            return True
        if any(
            isinstance(c, ast.With)
            and any("raises" in ast.unparse(i.context_expr) for i in c.items)
            for c in ast.walk(node)
        ):
            return True
    return False


def env_vars_read(source: str) -> set[str]:
    """Names of environment variables the source reads with a literal key."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = ast.unparse(node.func.value)
            if node.func.attr in {"get", "setdefault", "getenv", "pop"} and owner in {
                "os.environ",
                "os",
                "environ",
            }:
                if (
                    node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    names.add(node.args[0].value)
        elif (
            isinstance(node, ast.Subscript) and ast.unparse(node.value) == "os.environ"
        ):
            if isinstance(node.slice, ast.Constant) and isinstance(
                node.slice.value, str
            ):
                names.add(node.slice.value)
    return names


def missing_from_text(names: Iterable[str], text: str) -> list[str]:
    return sorted(n for n in names if f"`{n}`" not in text and f"{n}=" not in text)


_LINK = re.compile(r"\[[^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)")


def unresolved_links(
    markdown: str, base: Path, tracked: set[str], root: Path = ROOT
) -> list[str]:
    """Relative file links in a Markdown text that do not name a tracked file."""
    bad = []
    for target in _LINK.findall(markdown):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("mailto:"):
            continue
        resolved = (base / target).resolve()
        try:
            rel = resolved.relative_to(root).as_posix()
        except ValueError:
            bad.append(target)
            continue
        if rel not in tracked and not any(
            t.startswith(rel.rstrip("/") + "/") for t in tracked
        ):
            bad.append(target)
    return bad


def tracked_files() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout
    return set(out.split("\n")) - {""}


# ---- scorer ----------------------------------------------------------------

DOMAIN_SCRIPTS = {
    "project": "analyze_project.py",
    "dependencies": "audit_dependencies.py",
    "codebase": "analyze_codebase.py",
    "security": "analyze_security.py",
    "documentation": "audit_documentation.py",
    "architecture": "analyze_architecture.py",
    "concepts": "trace_concepts.py",
    "linters": "run_linters.py",
    "tests": "run_tests.py",
    "directory_density": "analyze_directory_density.py",
    "version_sync": "analyze_version_sync.py",
    "changelog": "audit_changelog.py",
    "pytest_quality": "grade_pytest.py",
    "env_vars": "scan_env_vars.py",
    "xdg": "analyze_xdg_kg.py",
}

NESTED_ENV = "AXIL_SOURCE_QUALITY_NESTED"


def scorer_dir() -> Path:
    import universal_skills

    return Path(universal_skills.__file__).parent / "core" / "code-enhancer" / "scripts"


def run_domain(domain: str, repo: Path = ROOT) -> dict:
    """Run one scorer domain script as the scorer does and return its JSON report."""
    env = dict(os.environ)
    env[NESTED_ENV] = "1"
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    proc = subprocess.run(
        [sys.executable, str(scorer_dir() / DOMAIN_SCRIPTS[domain]), str(repo)],
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
    )
    return json.loads(proc.stdout)


def gpa(grades: Iterable[str]) -> float:
    points = [GRADE_POINTS[g] for g in grades if g in GRADE_POINTS]
    return sum(points) / len(points) if points else 0.0


def score_passes(report: dict, threshold: int) -> bool:
    return report.get("score") is not None and report["score"] >= threshold


def grade_floor(grades: dict[str, str]) -> dict[str, str]:
    """Domains graded below B."""
    return {d: g for d, g in grades.items() if g not in ("A", "B")}


# ---- documentation and configuration ---------------------------------------

_SECRET_NAME = re.compile(
    r"(TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY|CREDENTIAL|PRIVATE_KEY)", re.I
)


def secret_assignments(env_text: str) -> list[str]:
    """Variables an env example assigns a non-empty value although their name marks a credential."""
    found = []
    for line in env_text.splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.+)$", line.strip())
        if match and _SECRET_NAME.search(match.group(1)):
            found.append(match.group(1))
    return found


def main_check_passes() -> bool:
    """The documented ``axil-package --check`` command accepts the default targets."""
    from axil.services import packaging_cli

    return packaging_cli.main(["--check"]) == 0


def pinned_hook_revisions(config_text: str) -> dict[str, str]:
    """Map each pre-commit repository's short name to its pinned revision."""
    pins: dict[str, str] = {}
    for match in re.finditer(r"- repo: (\S+)\s+rev: (\S+)", config_text):
        pins[match.group(1).rstrip("/").rsplit("/", 1)[-1]] = match.group(2)
    return pins


def changelog_names_rows(entry: dict, rows: Iterable[str]) -> bool:
    text = json.dumps(entry)
    return all(row in text for row in rows)


def names_contract(
    node: ast.FunctionDef | ast.AsyncFunctionDef, module_source: str, module_doc: str
) -> bool:
    """A significant function names its owning contract.

    It does so through its own docstring, a ``# spec:`` comment above it, or the
    ``CONCEPT:`` marker in the docstring of the module that owns it.
    """
    if (ast.get_docstring(node) or "").strip() or "CONCEPT:" in module_doc:
        return True
    lines = module_source.splitlines()
    start = max(0, node.lineno - 3)
    return any(re.search(r"#\s*spec:", line) for line in lines[start : node.lineno])


def calls(function: ast.FunctionDef, name: str) -> bool:
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            target = node.func
            if (isinstance(target, ast.Name) and target.id == name) or (
                isinstance(target, ast.Attribute) and target.attr == name
            ):
                return True
    return False


_PROBE = r"""
import json, sys
import httpx
from PySide6.QtWidgets import QApplication
import importlib
entry = importlib.import_module('axil.axil')

mode = sys.argv[1]
QApplication.exec = lambda self: 0
created = []
real_show = entry.Axil.show
def show(self):
    created.append(self)
    return real_show(self)
entry.Axil.show = show
code = None
try:
    entry.main()
except SystemExit as exc:
    code = exc.code

def handler(request):
    if mode == "denied":
        return httpx.Response(403, json={"status": "failed", "code": "FORBIDDEN", "error": "denied"}, request=request)
    return httpx.Response(200, json={"status": "success", "result": {}}, request=request)

window = created[0]
gateway = window.gateway
from axil.services.operation_registry import build_registry
gateway.operation_registry = build_registry([{"operation": "runs.get", "digest": "a" * 64}])
gateway._direct_http = httpx.AsyncClient(base_url=gateway.base_url, transport=httpx.MockTransport(handler))
import asyncio
answer = asyncio.run(gateway.fetch_run_summary("run-1"))
print(json.dumps({"exit": code, "windows": len(created), "answer": answer}))
"""


def served_entry_probe(*, authorized: bool) -> dict:
    """Launch the installed entry point and read one served operation as the client does."""
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE, "authorized" if authorized else "denied"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=100,
        env=env,
    )
    data = json.loads(proc.stdout.strip().splitlines()[-1])
    answer = data["answer"]
    if answer.get("status") == "failed":
        view = "unavailable"
    elif answer.get("status") == "success" and not answer.get("result"):
        view = "empty"
    else:
        view = "other"
    return {
        "entry": "launched" if data["exit"] == 0 and data["windows"] == 1 else "failed",
        "view": view,
    }


def concept_owners(registry_text: str) -> dict[str, str]:
    """Map each registered concept ID to the module named in its trailing ``(module)`` note."""
    owners: dict[str, str] = {}
    for match in re.finditer(
        r"^\s*- (GBOT-\d+\.\d+)\s*#(.*)$", registry_text, flags=re.M
    ):
        note = re.search(r"\(([a-z_][a-z0-9_]*)\)\s*$", match.group(2))
        owners[match.group(1)] = note.group(1) if note else ""
    return owners
