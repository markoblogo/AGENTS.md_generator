from __future__ import annotations

import shutil
from pathlib import Path

from agentsgen import actions as actions_module
from agentsgen import compat as compat_module
from agentsgen.config import ToolConfig
from agentsgen.detect import detect_repo


FIXTURES = Path(__file__).parent / "fixtures"


def _copy_fixture(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)


def test_actions_apply_pack_uses_public_site_manifest_seam(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)
    cfg = ToolConfig.from_detect(detect_repo(target))
    monkeypatch.setattr(
        actions_module,
        "build_site_llms_manifest",
        lambda site_url: f"# Patched manifest\n\nSource: {site_url}\n",
    )

    results = actions_module.apply_pack(
        target,
        cfg,
        autodetect=True,
        site_url="https://example.com",
        dry_run=False,
        print_diff=False,
    )

    assert any(result.action in {"created", "updated"} for result in results)
    llms = (target / "llms.txt").read_text(encoding="utf-8")
    assert "# Patched manifest" in llms


def test_actions_generated_json_helper_alias_is_compatible(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    result = compat_module._handle_generated_json_file(
        path,
        '{\n  "generated_by": "agentsgen"\n}\n',
        dry_run=False,
        print_diff=False,
    )

    assert result.action == "created"
    assert path.read_text(encoding="utf-8") == '{\n  "generated_by": "agentsgen"\n}\n'


def test_actions_no_longer_exports_legacy_underscore_helpers() -> None:
    assert not hasattr(actions_module, "_handle_generated_json_file")
    assert not hasattr(actions_module, "_handle_file")
    assert not hasattr(actions_module, "_write_or_diff")
    assert not hasattr(actions_module, "_generated_sibling_path")
    assert not hasattr(actions_module, "_unified_diff")
