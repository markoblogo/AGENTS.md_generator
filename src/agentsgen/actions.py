from __future__ import annotations

from pathlib import Path

from .config import ToolConfig
from . import config_io as _config_io
from . import pack_engine as _pack_engine
from . import patch_engine as _patch_engine
from .site_pack import build_site_llms_manifest

FileResult = _patch_engine.FileResult
load_tool_config = _config_io.load_tool_config
save_tool_config = _config_io.save_tool_config
generate_readme_snippets = _pack_engine.generate_readme_snippets
check_repo = _pack_engine.check_repo
run_core_check = _pack_engine.run_core_check
run_pack_check = _pack_engine.run_pack_check
run_snippets_check = _pack_engine.run_snippets_check
aggregate_check = _pack_engine.aggregate_check
status_repo = _pack_engine.status_repo
render_shared_blocks = _patch_engine.render_shared_blocks
render_all = _patch_engine.render_all
apply_config = _patch_engine.apply_config
init_or_update = _patch_engine.init_or_update
update_from_config = _patch_engine.update_from_config


def pack_plan_specs(
    target: Path,
    cfg: ToolConfig,
    *,
    autodetect: bool,
    site_url: str | None = None,
):
    return _pack_engine.pack_plan_specs(
        target,
        cfg,
        autodetect=autodetect,
        site_url=site_url,
        site_manifest_builder=build_site_llms_manifest,
    )


def apply_pack(
    target: Path,
    cfg: ToolConfig,
    *,
    autodetect: bool,
    site_url: str | None = None,
    dry_run: bool,
    print_diff: bool,
):
    return _pack_engine.apply_pack(
        target,
        cfg,
        autodetect=autodetect,
        site_url=site_url,
        site_manifest_builder=build_site_llms_manifest,
        dry_run=dry_run,
        print_diff=print_diff,
    )
