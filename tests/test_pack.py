from __future__ import annotations

import json
import shutil
from pathlib import Path

from agentsgen.actions import apply_pack, load_tool_config
from agentsgen.config import ToolConfig
from agentsgen.detect import detect_repo


FIXTURES = Path(__file__).parent / "fixtures"


def _copy_fixture(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)


def test_pack_python_uv_generates_bundle(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)

    cfg = ToolConfig.from_detect(detect_repo(target))
    results = apply_pack(target, cfg, autodetect=True, dry_run=False, print_diff=False)
    assert any(r.changed for r in results)

    assert (target / "llms.txt").is_file()
    assert (target / "docs" / "ai" / "how-to-run.md").is_file()
    assert (target / "docs" / "ai" / "how-to-test.md").is_file()
    assert (target / "docs" / "ai" / "architecture.md").is_file()
    assert (target / "docs" / "ai" / "data-contracts.md").is_file()
    assert (target / "SECURITY_AI.md").is_file()
    assert (target / "CONTRIBUTING_AI.md").is_file()
    assert (target / "README_SNIPPETS.md").is_file()
    assert (target / "agents.entrypoints.json").is_file()

    llms = (target / "llms.txt").read_text(encoding="utf-8")
    entrypoints = json.loads(
        (target / "agents.entrypoints.json").read_text(encoding="utf-8")
    )
    how_to_test = (target / "docs" / "ai" / "how-to-test.md").read_text(
        encoding="utf-8"
    )
    assert "uv run pytest" in llms
    assert "uv run pytest" in how_to_test
    assert entrypoints["version"] == 1
    assert entrypoints["commands"]


def test_pack_node_pnpm_uses_detected_commands(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "node_pnpm", target)

    cfg = ToolConfig.from_detect(detect_repo(target))
    results = apply_pack(target, cfg, autodetect=True, dry_run=False, print_diff=False)
    assert any(r.changed for r in results)

    llms = (target / "llms.txt").read_text(encoding="utf-8")
    run_guide = (target / "docs" / "ai" / "how-to-run.md").read_text(encoding="utf-8")
    assert "pnpm test" in llms
    assert "pnpm dev" in run_guide


def test_pack_no_markers_writes_generated_sibling(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "pack_no_markers", target)

    original = (target / "SECURITY_AI.md").read_text(encoding="utf-8")
    cfg = ToolConfig.from_detect(detect_repo(target))
    results = apply_pack(target, cfg, autodetect=True, dry_run=False, print_diff=False)

    assert (target / "SECURITY_AI.md").read_text(encoding="utf-8") == original
    generated = target / "SECURITY_AI.generated.md"
    assert generated.is_file()
    assert any(
        r.path.resolve() == generated.resolve() and r.action == "generated"
        for r in results
    )


def test_pack_entrypoints_prefers_config_and_uses_generated_sibling(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)
    (target / ".agentsgen.json").write_text(
        """{
  "version": 1,
  "project": {"name": "repo", "primary_stack": "python", "repo_root": "."},
  "commands": {
    "install": "uv sync --dev",
    "test": "uv run pytest -q",
    "lint": "uv run ruff check .",
    "run": "python -m app"
  },
  "pack": {
    "enabled": true,
    "llms_format": "txt",
    "output_dir": "docs/ai",
    "files": ["agents.entrypoints.json"]
  }
}
""",
        encoding="utf-8",
    )

    cfg = load_tool_config(target)
    results = apply_pack(target, cfg, autodetect=False, dry_run=False, print_diff=False)
    manifest = json.loads(
        (target / "agents.entrypoints.json").read_text(encoding="utf-8")
    )
    assert manifest["version"] == 1
    assert manifest["repo"]["autodetect"] is False
    assert any(entry["id"] == "install" for entry in manifest["commands"])
    assert any(entry["source"]["kind"] == "config" for entry in manifest["commands"])
    assert any(r.path.name == "agents.entrypoints.json" for r in results)

    (target / "agents.entrypoints.json").write_text(
        '{"version":1,"generated_by":"someone-else"}\n',
        encoding="utf-8",
    )
    results = apply_pack(target, cfg, autodetect=False, dry_run=False, print_diff=False)
    generated = target / "agents.entrypoints.generated.json"
    assert generated.is_file()
    assert any(
        r.path.resolve() == generated.resolve() and r.action == "generated"
        for r in results
    )
