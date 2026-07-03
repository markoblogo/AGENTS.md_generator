from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from agentsgen.cli import app
from agentsgen.validators import validate_fleet_scan_report_payload


FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def _copy_fixture(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)


def _make_git_repo(path: Path) -> None:
    (path / ".git").mkdir()


def _init_repo(path: Path) -> None:
    res = runner.invoke(
        app, ["init", str(path), "--defaults", "--autodetect", "--no-prompts"]
    )
    assert res.exit_code == 0, res.stdout


def test_fleet_scan_json_reports_repo_readiness_without_writes(tmp_path: Path) -> None:
    root = tmp_path / "fleet"
    root.mkdir()
    ready = root / "ready"
    _copy_fixture(FIXTURES / "python_uv", ready)
    _make_git_repo(ready)
    _init_repo(ready)
    raw = root / "raw"
    _copy_fixture(FIXTURES / "status_no_config", raw)
    _make_git_repo(raw)
    (raw / "AGENTS.md").write_text("# hand written\n", encoding="utf-8")
    (raw / "RUNBOOK.md").write_text("# hand written\n", encoding="utf-8")

    res = runner.invoke(app, ["fleet", "scan", str(root), "--format", "json"])

    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    validate_fleet_scan_report_payload(payload)
    assert payload["version"] == 1
    assert payload["command"] == "fleet scan"
    assert payload["summary"]["repos_count"] == 2
    assert payload["summary"]["needs_init_count"] == 1
    assert payload["summary"]["needs_manual_markers_count"] == 1
    repos = {Path(row["repo"]).name: row for row in payload["repos"]}
    assert repos["ready"]["has_config"] is True
    assert repos["raw"]["has_config"] is False
    assert (
        repos["raw"]["recommended_next"] == "agentsgen init . --defaults --autodetect"
    )
    assert not (raw / ".agentsgen.json").exists()


def test_fleet_scan_writes_markdown_and_json_outputs(tmp_path: Path) -> None:
    root = tmp_path / "fleet"
    repo = root / "repo"
    _copy_fixture(FIXTURES / "python_uv", repo)
    _make_git_repo(repo)
    _init_repo(repo)
    md_out = tmp_path / "fleet.md"
    json_out = tmp_path / "fleet.json"

    res = runner.invoke(
        app,
        [
            "fleet",
            "scan",
            str(root),
            "--out",
            str(md_out),
            "--json-out",
            str(json_out),
        ],
    )

    assert res.exit_code == 0, res.stdout
    assert md_out.exists()
    assert json_out.exists()
    assert "agentsgen fleet scan" in md_out.read_text(encoding="utf-8")
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    validate_fleet_scan_report_payload(payload)
    assert str(md_out) in res.stdout
    assert str(json_out) in res.stdout
