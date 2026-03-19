from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from agentsgen.cli import app
from agentsgen.constants import CONFIG_FILENAME


FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def _copy_fixture(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)


def test_status_no_config_reports_drift_json(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "status_no_config", target)

    res = runner.invoke(app, ["status", str(target), "--format", "json"])
    assert res.exit_code == 1
    payload = json.loads(res.stdout)
    assert payload["status"] == "drift"
    assert payload["config"]["present"] is False
    assert payload["summary"]["drift"] >= 1

    text_res = runner.invoke(app, ["status", str(target)])
    assert text_res.exit_code == 1
    assert f"- Missing {CONFIG_FILENAME}" in text_res.stdout


def test_status_generated_sibling_reports_drift_text(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "status_generated_sibling", target)

    res = runner.invoke(app, ["status", str(target)])
    assert res.exit_code == 1
    assert "Generated sibling exists for AGENTS.md: AGENTS.generated.md" in res.stdout
    assert "RUNBOOK.md: present, markers: no" in res.stdout
    assert "Summary: DRIFT" in res.stdout
