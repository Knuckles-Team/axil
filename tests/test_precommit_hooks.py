import tomllib
from pathlib import Path

import pytest
import yaml

CONFIG = Path(__file__).resolve().parent.parent / ".pre-commit-config.yaml"
PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
REQUIRED = ["spec", "secrets"]


@pytest.mark.spec("AXIL-CLIENT-R016.1")
def test_required_pipelines_hook_ids_present():
    text = CONFIG.read_text()
    for hook in REQUIRED:
        assert f"- id: {hook}\n" in text, hook
    py = PYPROJECT.read_text()
    assert "[tool.pipelines_hooks.public_surface]" in py
    assert "[tool.pipelines_hooks.ste]" in py


@pytest.mark.spec("AXIL-CLIENT-R016.2")
def test_canonical_shared_guardrails_preserve_client_boundary():
    text = CONFIG.read_text()
    for hook in (
        "no-legacy-concepts",
        "coupling",
        "lockfile-version-mirrors",
        "lane-guard",
    ):
        assert f"- id: {hook}\n" in text, hook
    owners = {repo["repo"]: repo for repo in yaml.safe_load(text)["repos"]}
    pipelines = owners["https://github.com/Knuckles-Team/pipelines"]
    manager = owners["https://github.com/Knuckles-Team/repository-manager"]
    assert pipelines["rev"] == "main"
    assert manager["rev"] == "09e91390d446950d345304c7a05fb69d86fdca8b"
    hooks = {hook["id"]: hook for hook in pipelines["hooks"]}
    assert {
        "no-legacy-concepts",
        "coupling",
        "lockfile-version-mirrors",
    } <= hooks.keys()
    assert [hook["id"] for hook in manager["hooks"]] == ["lane-guard"]
    assert hooks["coupling"]["args"] == ["--root", "."]
    mirrors = hooks["lockfile-version-mirrors"]
    assert mirrors["args"] == ["--root", "."]
    assert mirrors["always_run"] is False
    assert (
        mirrors["files"]
        == r"(^|/)(pyproject\.toml|uv\.lock|requirements[^/]*\.txt|setup\.(py|cfg))$"
    )
    for script in (
        "check_no_legacy_markers.py",
        "check_lane_guard.py",
        "check_coupling.py",
        "check_lockfile_version_mirrors.py",
    ):
        assert script not in text
    policy = tomllib.loads(PYPROJECT.read_text())["tool"]["pipelines_hooks"]
    assert policy["packages"] == ["axil"]
    assert set(policy["coupling"]["forbidden"]) == {
        "meristem",
        "epistemic_graph",
        "arbora",
        "agent_terminal_ui",
        "tuig",
        "agent_webui",
    }
    assert policy["coupling"]["allowed"] == ["arbora.client"]
