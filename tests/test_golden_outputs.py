from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from agentsgen.cli import app


FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = Path(__file__).parent / "golden"
runner = CliRunner()


def _copy_fixture(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)


def _stable_json(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "generated_at" in payload:
        payload["generated_at"] = ""
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def test_golden_python_uv_outputs(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)

    assert runner.invoke(
        app,
        ["init", str(target), "--defaults", "--autodetect", "--name", "repo"],
    ).exit_code == 0
    assert runner.invoke(app, ["pack", str(target), "--autodetect"]).exit_code == 0
    assert runner.invoke(app, ["understand", str(target)]).exit_code == 0

    assert (target / "AGENTS.md").read_text(encoding="utf-8") == (
        GOLDEN / "python_uv" / "AGENTS.md"
    ).read_text(encoding="utf-8")
    assert (target / "RUNBOOK.md").read_text(encoding="utf-8") == (
        GOLDEN / "python_uv" / "RUNBOOK.md"
    ).read_text(encoding="utf-8")
    assert _stable_json(target / "agents.entrypoints.json") == _stable_json(
        GOLDEN / "python_uv" / "agents.entrypoints.json"
    )
    assert _stable_json(target / "agents.knowledge.json") == _stable_json(
        GOLDEN / "python_uv" / "agents.knowledge.json"
    )


def test_golden_readme_snippets_output(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    for name in [
        "README.md",
        "pyproject.toml",
        "src",
        ".github",
        "tests",
        "scripts",
        "recipes",
        "docs",
    ]:
        source = Path.cwd() / name
        if source.is_dir():
            shutil.copytree(source, target / name, dirs_exist_ok=True)
        elif source.exists():
            (target / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target / name)

    assert runner.invoke(app, ["snippets", str(target)]).exit_code == 0
    assert (target / "README_SNIPPETS.generated.md").read_text(encoding="utf-8") == (
        GOLDEN / "repo" / "README_SNIPPETS.generated.md"
    ).read_text(encoding="utf-8")
