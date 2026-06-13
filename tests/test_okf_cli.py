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


def _prepare_repo_with_pack(target: Path) -> None:
    _copy_fixture(FIXTURES / "python_uv", target)
    res = runner.invoke(app, ["pack", str(target)])
    assert res.exit_code == 0


def test_okf_export_check_reports_drift_when_missing(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _prepare_repo_with_pack(target)

    res = runner.invoke(
        app,
        ["okf", "export", str(target), "--check", "--format", "json"],
    )
    assert res.exit_code == 1
    payload = json.loads(res.stdout)
    assert payload["status"] == "drift"
    assert any(
        str(row["path"]).endswith("docs/ai/okf/index.md") for row in payload["results"]
    )
    assert any(
        str(row["path"]).endswith("docs/ai/okf/repo/architecture.md")
        for row in payload["results"]
    )


def test_okf_export_writes_bundle_and_check_passes(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _prepare_repo_with_pack(target)

    first = runner.invoke(app, ["okf", "export", str(target)])
    assert first.exit_code == 0

    root_index = target / "docs" / "ai" / "okf" / "index.md"
    repo_index = target / "docs" / "ai" / "okf" / "repo" / "index.md"
    architecture = target / "docs" / "ai" / "okf" / "repo" / "architecture.md"
    entrypoints = target / "docs" / "ai" / "okf" / "assets" / "entrypoints.md"

    assert root_index.is_file()
    assert repo_index.is_file()
    assert architecture.is_file()
    assert entrypoints.is_file()

    architecture_text = architecture.read_text(encoding="utf-8")
    assert 'type: "Repo Guide"' in architecture_text
    assert 'title: "Architecture Overview"' in architecture_text
    assert 'canonical: "docs/ai/architecture.md"' in architecture_text

    entrypoints_text = entrypoints.read_text(encoding="utf-8")
    assert 'type: "Command Surface"' in entrypoints_text
    assert "Rendered from `agents.entrypoints.json`." in entrypoints_text
    assert "`test`" in entrypoints_text

    check = runner.invoke(
        app,
        ["okf", "export", str(target), "--check", "--format", "json"],
    )
    assert check.exit_code == 0
    payload = json.loads(check.stdout)
    assert payload["status"] == "ok"


def test_okf_export_dry_run_does_not_write_files(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _prepare_repo_with_pack(target)

    res = runner.invoke(
        app,
        ["okf", "export", str(target), "--dry-run", "--format", "json"],
    )
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["dry_run"] is True
    assert payload["status"] == "ok"
    assert not (target / "docs" / "ai" / "okf").exists()
