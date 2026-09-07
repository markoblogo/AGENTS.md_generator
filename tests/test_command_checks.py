import json
from pathlib import Path

from typer.testing import CliRunner
from agentsgen.cli import app
from agentsgen.command_checks import check_command_references
from agentsgen.config import ToolConfig
from agentsgen.model import ProjectInfo


def test_deleted_npm_script_fails_full_check(tmp_path: Path):
    runner = CliRunner()
    package = tmp_path / "package.json"
    package.write_text(
        json.dumps({"name": "example", "scripts": {"test": "vitest run"}})
    )
    (tmp_path / "README.md").write_text("# Example\n")
    assert (
        runner.invoke(
            app, ["init", str(tmp_path), "--defaults", "--autodetect"]
        ).exit_code
        == 0
    )
    assert runner.invoke(app, ["fix", str(tmp_path), "--all"]).exit_code == 0
    assert runner.invoke(app, ["check", str(tmp_path), "--all", "--ci"]).exit_code == 0
    package.write_text(json.dumps({"name": "example", "scripts": {}}))
    result = runner.invoke(app, ["check", str(tmp_path), "--all", "--format", "json"])
    assert result.exit_code == 1
    assert "has no script 'test'" in result.stdout


def test_make_missing_target_and_config_path(tmp_path: Path):
    (tmp_path / "Makefile").write_text("lint:\n\t@true\n")
    cfg = ToolConfig.from_project_info(
        ProjectInfo(
            "example",
            "python",
            commands={"test": "make test"},
            config_locations=["missing.toml"],
        )
    )
    problems, _ = check_command_references(tmp_path, cfg)
    assert any("no target 'test'" in p for p in problems)
    assert any("missing.toml: missing" in p for p in problems)


def test_unknown_and_dynamic_commands_are_not_executed(tmp_path: Path):
    cfg = ToolConfig.from_project_info(
        ProjectInfo(
            "example",
            "python",
            commands={"test": "touch SENTINEL; pytest", "lint": "custom-lint"},
        )
    )
    problems, warnings = check_command_references(tmp_path, cfg)
    assert not problems
    assert len(warnings) == 2
    assert not (tmp_path / "SENTINEL").exists()


def test_quickstart_without_readme_and_full_fix(tmp_path: Path):
    runner = CliRunner()
    assert (
        runner.invoke(
            app, ["init", str(tmp_path), "--defaults", "--autodetect"]
        ).exit_code
        == 0
    )
    assert runner.invoke(app, ["check", str(tmp_path), "--ci"]).exit_code == 0
    assert runner.invoke(app, ["fix", str(tmp_path), "--all"]).exit_code == 0
    result = runner.invoke(app, ["check", str(tmp_path), "--all", "--ci"])
    assert result.exit_code == 0, result.stdout
    assert "snippets: skipped" in result.stdout


def test_managed_body_drift_is_detected_and_handwritten_text_preserved(tmp_path: Path):
    runner = CliRunner()
    assert runner.invoke(app, ["init", str(tmp_path), "--defaults"]).exit_code == 0
    path = tmp_path / "AGENTS.md"
    original = path.read_text()
    path.write_text(
        original.replace(
            "Keep changes small and verifiable.", "Changed generated policy."
        )
        + "\nMy handwritten policy.\n"
    )
    result = runner.invoke(app, ["check", str(tmp_path), "--ci"])
    assert result.exit_code == 1
    assert runner.invoke(app, ["update", str(tmp_path)]).exit_code == 0
    assert "My handwritten policy." in path.read_text()
    assert runner.invoke(app, ["check", str(tmp_path), "--ci"]).exit_code == 0
