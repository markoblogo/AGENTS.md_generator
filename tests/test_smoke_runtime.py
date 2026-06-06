from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agentsgen.actions import apply_config, save_tool_config
from agentsgen.config import ToolConfig
from agentsgen.model import ProjectInfo


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_init_creates_files_and_config() -> None:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td)
        info = ProjectInfo(project_name="demo", stack="node").normalized()
        info.package_manager = "npm"
        info.commands = {
            "install": "npm install",
            "dev": "npm run dev",
            "test": "npm test",
        }
        cfg = ToolConfig.from_project_info(info)
        save_tool_config(target, cfg)
        apply_config(target, cfg, write_prompts=True, dry_run=False, print_diff=False)

        assert (target / ".agentsgen.json").is_file()
        assert (target / "AGENTS.md").is_file()
        assert (target / "RUNBOOK.md").is_file()
        assert (target / "prompt" / "execspec.md").is_file()

        payload = json.loads(_read(target / ".agentsgen.json"))
        assert payload["version"] == 1
        assert payload["project"]["name"] == "demo"


def test_update_preserves_outside_markers() -> None:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td)
        info = ProjectInfo(project_name="demo", stack="node").normalized()
        info.package_manager = "npm"
        info.commands = {
            "install": "npm install",
            "dev": "npm run dev",
            "test": "npm test",
        }
        cfg = ToolConfig.from_project_info(info)
        save_tool_config(target, cfg)
        apply_config(target, cfg, write_prompts=False, dry_run=False, print_diff=False)

        agents = target / "AGENTS.md"
        agents.write_text(
            _read(agents) + "\n## User Notes\n\nDo not delete this.\n",
            encoding="utf-8",
        )

        info.commands["test"] = "npm test -- --runInBand"
        save_tool_config(target, ToolConfig.from_project_info(info))
        apply_config(
            target,
            ToolConfig.from_project_info(info),
            write_prompts=False,
            dry_run=False,
            print_diff=False,
        )

        updated = _read(agents)
        assert "## User Notes" in updated
        assert "Do not delete this." in updated
        assert "npm test -- --runInBand" in updated


def test_no_markers_creates_generated_files() -> None:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td)
        (target / "AGENTS.md").write_text("# Custom AGENTS\nNo markers here\n", encoding="utf-8")
        (target / "RUNBOOK.md").write_text("# Custom RUNBOOK\nNo markers here\n", encoding="utf-8")

        info = ProjectInfo(project_name="demo", stack="node").normalized()
        info.package_manager = "npm"
        info.commands = {
            "install": "npm install",
            "dev": "npm run dev",
            "test": "npm test",
        }

        cfg = ToolConfig.from_project_info(info)
        save_tool_config(target, cfg)
        apply_config(target, cfg, write_prompts=False, dry_run=False, print_diff=False)

        assert (target / "AGENTS.generated.md").is_file()
        assert (target / "RUNBOOK.generated.md").is_file()
        assert _read(target / "AGENTS.md") == "# Custom AGENTS\nNo markers here\n"
