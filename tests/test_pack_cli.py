from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from agentsgen.cli import app


FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def _copy_fixture(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)


def test_pack_check_reports_drift_json(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)

    res = runner.invoke(app, ["pack", str(target), "--check", "--format", "json"])
    assert res.exit_code == 1
    payload = json.loads(res.stdout)
    assert payload["status"] == "drift"
    assert any(r["action"] == "created" for r in payload["results"])


def test_pack_check_passes_after_pack(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "node_pnpm", target)

    first = runner.invoke(app, ["pack", str(target)])
    assert first.exit_code == 0

    check = runner.invoke(app, ["pack", str(target), "--check", "--format", "json"])
    assert check.exit_code == 0
    payload = json.loads(check.stdout)
    assert payload["status"] == "ok"


def test_pack_json_output_includes_results(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)

    res = runner.invoke(
        app, ["pack", str(target), "--dry-run", "--format", "json", "--files", "llms"]
    )
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["status"] == "ok"
    assert payload["dry_run"] is True
    assert isinstance(payload["results"], list)
    assert len(payload["results"]) >= 1


def test_pack_print_plan_json_no_write(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)

    res = runner.invoke(
        app,
        ["pack", str(target), "--autodetect", "--print-plan", "--format", "json"],
    )
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["version"] == 1
    assert payload["print_plan"] is True
    assert any(str(row.get("path", "")).endswith("llms.txt") for row in payload["plan"])
    assert not (target / "llms.txt").exists()


def test_pack_print_plan_check_reports_drift_without_writes(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)

    res = runner.invoke(
        app,
        [
            "pack",
            str(target),
            "--autodetect",
            "--print-plan",
            "--check",
            "--format",
            "json",
        ],
    )
    assert res.exit_code == 1
    payload = json.loads(res.stdout)
    assert payload["version"] == 1
    assert payload["check"] is True
    assert payload["print_plan"] is True
    assert payload["status"] == "drift"
    assert not (target / "llms.txt").exists()


def test_pack_print_plan_text_includes_header(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)

    res = runner.invoke(app, ["pack", str(target), "--autodetect", "--print-plan"])
    assert res.exit_code == 0
    assert f"repo: {target.resolve()}" in res.stdout
    assert "autodetect: on" in res.stdout
    assert "output_dir: docs/ai" in res.stdout
    assert "files_count: " in res.stdout
