from __future__ import annotations

import json
from pathlib import Path

from agentsgen.detect import detect_repo


FIXTURES = Path(__file__).parent / "fixtures"


def test_detect_python_uv() -> None:
    repo = FIXTURES / "python_uv"
    res = detect_repo(repo)
    assert res.project.get("primary_stack") == "python"
    assert res.project.get("python_toolchain") == "uv"
    assert "uv.lock" in res.to_json()["evidence"]["python"]
    assert "test" in res.commands
    assert "pytest" in res.commands["test"]


def test_detect_python_poetry() -> None:
    repo = FIXTURES / "python_poetry"
    res = detect_repo(repo)
    assert res.project.get("primary_stack") == "python"
    assert res.project.get("python_toolchain") == "poetry"
    assert "poetry.lock" in res.to_json()["evidence"]["python"]
    assert "test" in res.commands
    assert res.commands["test"].startswith("poetry run")


def test_detect_node_pnpm() -> None:
    repo = FIXTURES / "node_pnpm"
    res = detect_repo(repo)
    assert res.project.get("primary_stack") == "node"
    assert res.project.get("node_package_manager") == "pnpm"
    assert res.commands.get("test", "").startswith("pnpm")
    assert res.commands.get("dev", "").startswith("pnpm")


def test_makefile_dominates_scripts_and_python() -> None:
    repo = FIXTURES / "makefile_dominant"
    res = detect_repo(repo)
    # Commands must be make-based.
    assert res.commands.get("test") == "make test"
    assert res.commands.get("lint") == "make lint"


def test_monorepo_mixed_no_root_commands() -> None:
    repo = FIXTURES / "monorepo_mixed"
    res = detect_repo(repo)
    assert res.project.get("primary_stack") == "mixed"
    # No Makefile in root, so commands should be empty (avoid hallucinating).
    assert res.commands == {}
    # Evidence should mention both sides.
    ev = res.to_json()["evidence"]
    assert any("package.json" in x for x in ev["node"])
    assert any("pyproject.toml" in x for x in ev["python"])
