from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .actions import apply_pack, load_tool_config, save_tool_config
from .config import ToolConfig, merge_detect_hints
from .detect import detect_repo
from .llm import LLMEnhancementResult, LLMOptions
from .pack_engine import pack_plan_specs
from .patch_engine import apply_config_detailed, update_from_config_detailed
from .presets import load_preset_config
from .result_types import FileResult
from .stacks import adapter_for
from .stacks.base import project_name_from_dir


@dataclass(frozen=True)
class InitFlowResult:
    config: ToolConfig
    config_written: bool
    results: list[FileResult]
    llm_result: LLMEnhancementResult | None


@dataclass(frozen=True)
class PackFlowResult:
    config: ToolConfig
    results: list[FileResult]
    status: str
    summary: str
    drift: bool
    check: bool
    dry_run: bool


def _default_config_for_target(
    target: Path,
    *,
    stack: str | None,
    name: str | None,
) -> ToolConfig:
    resolved_stack = (stack or "static").strip().lower() or "static"
    if resolved_stack == "mixed":
        resolved_stack = "static"
    adapter = adapter_for(resolved_stack)
    project_name = (name or project_name_from_dir(target)).strip()
    info = adapter.default_info(target, project_name)
    return ToolConfig.from_project_info(info)


def resolve_init_config(
    target: Path,
    *,
    stack: str | None = None,
    name: str | None = None,
    preset: str | None = None,
    autodetect: bool = True,
    force_config: bool = False,
) -> tuple[ToolConfig, bool]:
    cfg_path = target / ".agentsgen.json"
    config_written = False
    cfg: ToolConfig
    preset_cfg: ToolConfig | None = None

    if preset:
        preset_cfg = load_preset_config(preset)

    if cfg_path.exists() and not force_config:
        cfg = load_tool_config(target)
        if autodetect:
            det_cfg = ToolConfig.from_detect(detect_repo(target))
            cfg = merge_detect_hints(cfg, det_cfg)
            config_written = True
        return cfg, config_written

    if preset_cfg is not None:
        cfg = preset_cfg
        if autodetect:
            cfg = merge_detect_hints(cfg, ToolConfig.from_detect(detect_repo(target)))
        if name:
            cfg.project["name"] = name
        if stack:
            cfg.project["primary_stack"] = stack
        return ToolConfig.from_json(cfg.to_json()), True

    if autodetect:
        cfg = ToolConfig.from_detect(detect_repo(target))
        if name:
            cfg.project["name"] = name
        if stack:
            cfg.project["primary_stack"] = stack
        return ToolConfig.from_json(cfg.to_json()), True

    return _default_config_for_target(target, stack=stack, name=name), True


def run_init_flow(
    target: Path,
    *,
    stack: str | None = None,
    name: str | None = None,
    preset: str | None = None,
    autodetect: bool = True,
    force_config: bool = False,
    prompts: bool = True,
    dry_run: bool = False,
    print_diff: bool = False,
    llm_options: LLMOptions | None = None,
) -> InitFlowResult:
    cfg, config_written = resolve_init_config(
        target,
        stack=stack,
        name=name,
        preset=preset,
        autodetect=autodetect,
        force_config=force_config,
    )
    if config_written and not dry_run:
        save_tool_config(target, cfg)
    normalized_llm = (llm_options or LLMOptions.disabled()).normalized()
    results, llm_result = apply_config_detailed(
        target,
        cfg,
        write_prompts=prompts,
        dry_run=dry_run,
        print_diff=print_diff,
        llm_provider=normalized_llm.provider if normalized_llm.enabled else "",
    )
    return InitFlowResult(
        config=cfg,
        config_written=bool(config_written and not dry_run),
        results=results,
        llm_result=llm_result,
    )


def run_update_flow(
    target: Path,
    *,
    dry_run: bool = False,
    print_diff: bool = False,
    llm_options: LLMOptions | None = None,
) -> tuple[list[FileResult], LLMEnhancementResult | None]:
    normalized_llm = (llm_options or LLMOptions.disabled()).normalized()
    return update_from_config_detailed(
        target,
        dry_run=dry_run,
        print_diff=print_diff,
        llm_provider=normalized_llm.provider if normalized_llm.enabled else "",
    )


def resolve_pack_config(
    target: Path,
    *,
    autodetect: bool = True,
    stack: str | None = None,
    llms_format: str | None = None,
    output_dir: str | None = None,
    files: list[str] | None = None,
) -> ToolConfig:
    cfg_path = target / ".agentsgen.json"
    cfg = load_tool_config(target) if cfg_path.exists() else ToolConfig()

    if autodetect:
        det_cfg = ToolConfig.from_detect(detect_repo(target))
        existing_pack = cfg.pack
        cfg = merge_detect_hints(cfg, det_cfg)
        cfg.pack = existing_pack
    elif not cfg_path.exists():
        cfg = _default_config_for_target(target, stack=stack, name=None)

    if stack:
        cfg.project["primary_stack"] = stack.strip().lower()
        cfg = ToolConfig.from_json(cfg.to_json())
    if llms_format:
        cfg.pack.llms_format = llms_format.strip().lower()
    if output_dir:
        cfg.pack.output_dir = output_dir.strip()
    if files is not None:
        cfg.pack.files = [item.strip() for item in files if item.strip()]
    return cfg


def run_pack_flow(
    target: Path,
    *,
    autodetect: bool = True,
    stack: str | None = None,
    llms_format: str | None = None,
    output_dir: str | None = None,
    files: list[str] | None = None,
    site: str | None = None,
    check: bool = False,
    dry_run: bool = False,
    print_diff: bool = False,
) -> PackFlowResult:
    cfg = resolve_pack_config(
        target,
        autodetect=autodetect,
        stack=stack,
        llms_format=llms_format,
        output_dir=output_dir,
        files=files,
    )
    dry_run_effective = dry_run or check
    results = apply_pack(
        target,
        cfg,
        autodetect=autodetect,
        site_url=site,
        dry_run=dry_run_effective,
        print_diff=print_diff,
    )
    errors = [row for row in results if row.action == "error"]
    drift = any(
        row.action in ("created", "updated", "generated") and row.changed
        for row in results
    )
    status = "error" if errors else ("drift" if check and drift else "ok")
    summary = (
        f"pack:{status} "
        f"(created={sum(1 for row in results if row.action == 'created')}, "
        f"updated={sum(1 for row in results if row.action == 'updated')}, "
        f"generated={sum(1 for row in results if row.action == 'generated')}, "
        f"errors={len(errors)})"
    )
    return PackFlowResult(
        config=cfg,
        results=results,
        status=status,
        summary=summary,
        drift=drift,
        check=check,
        dry_run=dry_run_effective,
    )


def plan_pack_sections(
    target: Path,
    cfg: ToolConfig,
    *,
    autodetect: bool,
) -> dict[str, list[str]]:
    return {
        str(rel).replace("\\", "/"): sections
        for rel, sections in pack_plan_specs(target, cfg, autodetect=autodetect)
    }
