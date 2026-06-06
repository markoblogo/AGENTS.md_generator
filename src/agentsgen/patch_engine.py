from __future__ import annotations

import difflib
from pathlib import Path

from .constants import AGENTS_FILENAME, PROMPTS_DIRNAME, RUNBOOK_FILENAME
from .generate import (
    render_agents_md,
    render_runbook_md,
    required_sections,
    required_runbook_sections,
    template_paths,
)
from .config import ToolConfig
from .config_io import load_tool_config
from .io_utils import read_text, write_text_atomic
from .markers import extract_section_content, has_any_agentsgen_markers, replace_section_content
from .model import ProjectInfo
from .normalize import normalize_markdown
from .result_types import FileResult
from .shared_sections import render_all_shared
from .templates import prompt_template_path, templates_base_dir
from .llm import LLMEnhancementRequest, LLMEnhancementResult, enhance_sections


def unified_diff(path: Path, old: str, new: str) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )


def generated_sibling_path(path: Path, generated_suffix: str = ".generated") -> Path:
    return path.with_name(f"{path.stem}{generated_suffix}{path.suffix}")


def patch_existing_with_generated(
    existing: str, generated: str, sections: list[str]
) -> tuple[str, list[str]]:
    missing: list[str] = []
    for sec in sections:
        body = extract_section_content(generated, sec)
        if body is None:
            missing.append(sec)
            continue
        existing, ok = replace_section_content(existing, sec, body)
        if not ok:
            missing.append(sec)
    return existing, missing


def write_or_diff(
    path: Path, new_content: str, dry_run: bool, print_diff: bool
) -> tuple[bool, str]:
    new_normalized = normalize_markdown(new_content)
    if path.exists():
        old_normalized = normalize_markdown(read_text(path))
        if old_normalized == new_normalized:
            return False, ""
        diff = unified_diff(path, old_normalized, new_normalized) if print_diff else ""
        if not dry_run:
            write_text_atomic(path, new_normalized)
        return True, diff
    diff = unified_diff(path, "", new_normalized) if print_diff else ""
    if not dry_run:
        write_text_atomic(path, new_normalized)
    return True, diff


def handle_file(
    path: Path,
    generated_full: str,
    *,
    required: list[str],
    dry_run: bool,
    print_diff: bool,
) -> FileResult:
    if not path.exists():
        changed, diff = write_or_diff(path, generated_full, dry_run, print_diff)
        return FileResult(
            path=path,
            action="created",
            message="created managed file",
            changed=changed,
            diff=diff,
        )

    existing = read_text(path)
    if not has_any_agentsgen_markers(existing):
        generated_path = generated_sibling_path(path)
        changed, diff = write_or_diff(generated_path, generated_full, dry_run, print_diff)
        return FileResult(
            path=generated_path,
            action="generated",
            message=f"markers missing in {path.name}; wrote generated sibling",
            changed=changed,
            diff=diff,
        )

    patched, missing = patch_existing_with_generated(existing, generated_full, required)
    if missing:
        return FileResult(
            path=path,
            action="error",
            message=f"missing required managed sections: {', '.join(missing)}",
            changed=False,
        )
    changed, diff = write_or_diff(path, patched, dry_run, print_diff)
    return FileResult(
        path=path,
        action="updated" if changed else "skipped",
        message="updated managed sections" if changed else "already up to date",
        changed=changed,
        diff=diff,
    )


def render_shared_blocks(
    cfg: ToolConfig,
    *,
    llm_provider: str = "",
    target: Path | None = None,
) -> dict[str, str]:
    blocks, _ = render_shared_blocks_detailed(
        cfg,
        llm_provider=llm_provider,
        target=target,
    )
    return blocks


def render_shared_blocks_detailed(
    cfg: ToolConfig,
    *,
    llm_provider: str = "",
    target: Path | None = None,
) -> tuple[dict[str, str], LLMEnhancementResult | None]:
    ctx = {
        "project": cfg.project or {},
        "paths": cfg.paths or {},
        "commands": cfg.commands or {},
        "defaults": cfg.defaults or {},
    }
    blocks = render_all_shared(ctx)
    enhancement: LLMEnhancementResult | None = None
    if llm_provider and target is not None:
        enhancement = enhance_sections(
            LLMEnhancementRequest(target=target, provider=llm_provider)
        )
        for section, extra in enhancement.sections.items():
            base = blocks.get(section, "").strip()
            blocks[section] = (
                f"{base}\n\n{extra.strip()}" if base and extra.strip() else extra.strip()
            )
    return blocks, enhancement


def render_all(
    cfg: ToolConfig,
    *,
    llm_provider: str = "",
    target: Path | None = None,
) -> tuple[str, str]:
    info = cfg.project_info
    base = templates_base_dir()
    agents_tpl, runbook_tpl = template_paths(base, info.stack)

    configs_hint = (
        ", ".join([f"`{p}`" for p in info.config_locations])
        if info.config_locations
        else "(not specified)"
    )
    single_test_hint = (
        info.commands.get("single_test", "") or "(not specified)"
    ).strip()
    shared = render_shared_blocks(cfg, llm_provider=llm_provider, target=target)

    agents_md = render_agents_md(
        info,
        agents_tpl,
        single_test_hint=single_test_hint,
        configs_hint=configs_hint,
        shared_blocks=shared,
    )
    runbook_md = render_runbook_md(info, runbook_tpl)

    return normalize_markdown(agents_md), normalize_markdown(runbook_md)


def apply_config(
    target: Path,
    cfg: ToolConfig,
    *,
    write_prompts: bool,
    dry_run: bool,
    print_diff: bool,
    llm_provider: str = "",
) -> list[FileResult]:
    results, _ = apply_config_detailed(
        target,
        cfg,
        write_prompts=write_prompts,
        dry_run=dry_run,
        print_diff=print_diff,
        llm_provider=llm_provider,
    )
    return results


def apply_config_detailed(
    target: Path,
    cfg: ToolConfig,
    *,
    write_prompts: bool,
    dry_run: bool,
    print_diff: bool,
    llm_provider: str = "",
) -> tuple[list[FileResult], LLMEnhancementResult | None]:
    results: list[FileResult] = []
    llm_result: LLMEnhancementResult | None = None

    if llm_provider:
        shared_blocks, llm_result = render_shared_blocks_detailed(
            cfg,
            llm_provider=llm_provider,
            target=target,
        )
        info = cfg.project_info
        base = templates_base_dir()
        agents_tpl, runbook_tpl = template_paths(base, info.stack)
        configs_hint = (
            ", ".join([f"`{p}`" for p in info.config_locations])
            if info.config_locations
            else "(not specified)"
        )
        single_test_hint = (
            info.commands.get("single_test", "") or "(not specified)"
        ).strip()
        agents_full = render_agents_md(
            info,
            agents_tpl,
            single_test_hint=single_test_hint,
            configs_hint=configs_hint,
            shared_blocks=shared_blocks,
        )
        runbook_full = render_runbook_md(info, runbook_tpl)
        agents_full = normalize_markdown(agents_full)
        runbook_full = normalize_markdown(runbook_full)
    else:
        agents_full, runbook_full = render_all(
            cfg, llm_provider=llm_provider, target=target
        )

    results.append(
        handle_file(
            target / AGENTS_FILENAME,
            agents_full,
            required=required_sections(cfg.project_info.stack),
            dry_run=dry_run,
            print_diff=print_diff,
        )
    )
    results.append(
        handle_file(
            target / RUNBOOK_FILENAME,
            runbook_full,
            required=required_runbook_sections(),
            dry_run=dry_run,
            print_diff=print_diff,
        )
    )

    if write_prompts:
        prompt_dir = target / PROMPTS_DIRNAME
        prompt_path = prompt_dir / "execspec.md"
        tpl = prompt_template_path("execspec.md")
        prompt_content = normalize_markdown(tpl.read_text(encoding="utf-8"))
        changed, diff = write_or_diff(
            prompt_path, prompt_content, dry_run=dry_run, print_diff=print_diff
        )
        results.append(
            FileResult(
                path=prompt_path,
                action="created"
                if not prompt_path.exists()
                else ("updated" if changed else "skipped"),
                message="prompt written" if changed else "prompt unchanged",
                changed=changed,
                diff=diff,
            )
        )

    return results, llm_result


def init_or_update(
    target: Path,
    info: ProjectInfo,
    write_prompts: bool,
    dry_run: bool,
    print_diff: bool,
    llm_provider: str = "",
) -> list[FileResult]:
    cfg = ToolConfig.from_project_info(info.normalized())
    return apply_config(
        target,
        cfg,
        write_prompts=write_prompts,
        dry_run=dry_run,
        print_diff=print_diff,
        llm_provider=llm_provider,
    )


def init_or_update_detailed(
    target: Path,
    info: ProjectInfo,
    write_prompts: bool,
    dry_run: bool,
    print_diff: bool,
    llm_provider: str = "",
) -> tuple[list[FileResult], LLMEnhancementResult | None]:
    cfg = ToolConfig.from_project_info(info.normalized())
    return apply_config_detailed(
        target,
        cfg,
        write_prompts=write_prompts,
        dry_run=dry_run,
        print_diff=print_diff,
        llm_provider=llm_provider,
    )


def update_from_config(
    target: Path, dry_run: bool, print_diff: bool, llm_provider: str = ""
) -> list[FileResult]:
    results, _ = update_from_config_detailed(
        target,
        dry_run=dry_run,
        print_diff=print_diff,
        llm_provider=llm_provider,
    )
    return results


def update_from_config_detailed(
    target: Path, dry_run: bool, print_diff: bool, llm_provider: str = ""
) -> tuple[list[FileResult], LLMEnhancementResult | None]:
    tool_cfg = load_tool_config(target)
    return apply_config_detailed(
        target,
        tool_cfg,
        write_prompts=False,
        dry_run=dry_run,
        print_diff=print_diff,
        llm_provider=llm_provider,
    )
