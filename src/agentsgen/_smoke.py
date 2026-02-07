from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from agentsgen.actions import apply_config, save_tool_config
from agentsgen.config import ToolConfig
from agentsgen.model import ProjectInfo


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test1_init_creates_files_and_config() -> None:
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
        res = apply_config(target, cfg, write_prompts=True, dry_run=False, print_diff=False)

        assert (target / ".agentsgen.json").is_file()
        assert (target / "AGENTS.md").is_file()
        assert (target / "RUNBOOK.md").is_file()
        assert (target / "prompt" / "execspec.md").is_file()

        cfg = json.loads(_read(target / ".agentsgen.json"))
        assert cfg["version"] == 1
        assert cfg["project"]["name"] == "demo"


def test2_update_preserves_outside_markers() -> None:
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
        original = _read(agents)
        # Add user content outside markers at end.
        agents.write_text(original + "\n## User Notes\n\nDo not delete this.\n", encoding="utf-8")

        # Change a command and re-run.
        info.commands["test"] = "npm test -- --runInBand"
        cfg = ToolConfig.from_project_info(info)
        save_tool_config(target, cfg)
        apply_config(target, cfg, write_prompts=False, dry_run=False, print_diff=False)

        updated = _read(agents)
        assert "## User Notes" in updated
        assert "Do not delete this." in updated
        assert "npm test -- --runInBand" in updated


def test3_no_markers_creates_generated_files() -> None:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td)
        agents = target / "AGENTS.md"
        runbook = target / "RUNBOOK.md"
        agents.write_text("# Custom AGENTS\nNo markers here\n", encoding="utf-8")
        runbook.write_text("# Custom RUNBOOK\nNo markers here\n", encoding="utf-8")

        info = ProjectInfo(project_name="demo", stack="node").normalized()
        info.package_manager = "npm"
        info.commands = {
            "install": "npm install",
            "dev": "npm run dev",
            "test": "npm test",
        }

        cfg = ToolConfig.from_project_info(info)
        save_tool_config(target, cfg)
        res = apply_config(target, cfg, write_prompts=False, dry_run=False, print_diff=False)

        assert agents.is_file()
        assert runbook.is_file()
        assert (target / "AGENTS.generated.md").is_file()
        assert (target / "RUNBOOK.generated.md").is_file()

        # Original untouched.
        assert _read(agents) == "# Custom AGENTS\nNo markers here\n"


def main() -> None:
    tests = [
        test1_init_creates_files_and_config,
        test2_update_preserves_outside_markers,
        test3_no_markers_creates_generated_files,
    ]

    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")

    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
