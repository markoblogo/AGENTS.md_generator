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


def _init_repo(target: Path) -> None:
    res = runner.invoke(
        app, ["init", str(target), "--defaults", "--autodetect", "--no-prompts"]
    )
    assert res.exit_code == 0, res.stdout


def test_check_aggregate_core_ok_pack_drift_json_and_ci(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "check_aggregate_core_ok_pack_drift", target)
    _init_repo(target)

    res = runner.invoke(app, ["check", str(target), "--format", "json", "--pack-check"])
    assert res.exit_code == 1
    payload = json.loads(res.stdout)
    assert payload["version"] == 1
    assert payload["command"] == "check"
    assert payload["status"] == "drift"
    assert payload["checks"]["core"]["status"] == "ok"
    assert payload["checks"]["pack"]["status"] == "drift"
    assert payload["checks"]["snippets"] is None
    assert payload["summary"]["drift_count"] >= 1

    ci = runner.invoke(app, ["check", str(target), "--pack-check", "--ci"])
    assert ci.exit_code == 1
    assert "agentsgen check: DRIFT" in ci.stdout
    assert "core: ok" in ci.stdout
    assert "pack: drift" in ci.stdout
    assert "snippets: skipped" in ci.stdout
    assert "agentsgen pack . --autodetect" in ci.stdout


def test_check_aggregate_core_drift_pack_ok_json(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "check_aggregate_core_drift_pack_ok", target)
    _init_repo(target)

    pack = runner.invoke(app, ["pack", str(target), "--autodetect"])
    assert pack.exit_code == 0, pack.stdout
    (target / "AGENTS.md").unlink()

    res = runner.invoke(app, ["check", str(target), "--format", "json", "--pack-check"])
    assert res.exit_code == 1
    payload = json.loads(res.stdout)
    assert payload["status"] == "drift"
    assert payload["checks"]["core"]["status"] == "drift"
    assert payload["checks"]["pack"]["status"] == "ok"
    assert any(
        item["message"] == "Missing AGENTS.md. Run: agentsgen init"
        for item in payload["checks"]["core"]["results"]
        if item["level"] == "problem"
    )


def test_check_aggregate_snippets_check_json(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "check_aggregate_snippets", target)
    _init_repo(target)

    res = runner.invoke(
        app, ["check", str(target), "--format", "json", "--snippets-check"]
    )
    assert res.exit_code == 1
    payload = json.loads(res.stdout)
    assert payload["status"] == "drift"
    assert payload["checks"]["core"]["status"] == "ok"
    assert payload["checks"]["pack"] is None
    assert payload["checks"]["snippets"]["status"] == "drift"
    assert payload["checks"]["snippets"]["raw"]["output_path"].endswith(
        "README_SNIPPETS.generated.md"
    )
