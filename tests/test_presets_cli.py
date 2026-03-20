from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agentsgen.cli import app


runner = CliRunner()
EXPECTED_PRESETS = [
    "python-lib",
    "fastapi",
    "nextjs",
    "monorepo-js",
    "cli-python",
    "cli-node",
]


def test_presets_command_lists_expected_presets() -> None:
    res = runner.invoke(app, ["presets"])
    assert res.exit_code == 0
    for name in EXPECTED_PRESETS:
        assert f"- {name}:" in res.stdout
        assert f"agentsgen init . --preset {name}" in res.stdout


def test_init_preset_nextjs_writes_expected_config(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()

    res = runner.invoke(
        app,
        ["init", str(target), "--preset", "nextjs", "--defaults", "--no-autodetect"],
    )
    assert res.exit_code == 0

    cfg = json.loads((target / ".agentsgen.json").read_text())
    assert cfg["presets"]["selected"] == "nextjs"
    assert cfg["project"]["primary_stack"] == "node"
    assert cfg["commands"]["dev"] == "pnpm dev || npm run dev"
    assert cfg["commands"]["build"] == "pnpm build || npm run build"
    assert (target / "AGENTS.md").exists()
    assert (target / "RUNBOOK.md").exists()


def test_init_invalid_preset_suggests_presets_command(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()

    res = runner.invoke(
        app, ["init", str(target), "--preset", "nope", "--defaults", "--no-autodetect"]
    )
    assert res.exit_code == 1
    assert "Unknown preset 'nope'" in res.stdout
    assert "agentsgen presets" in res.stdout
