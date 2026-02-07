from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

from .constants import (
    AGENTS_FILENAME,
    AGENTS_GENERATED_FILENAME,
    CONFIG_FILENAME,
    PROMPTS_DIRNAME,
    RUNBOOK_FILENAME,
    RUNBOOK_GENERATED_FILENAME,
)
from .generate import render_agents_md, render_runbook_md, required_sections, template_paths
from .generate import required_runbook_sections
from .io_utils import read_json, read_text, write_json_atomic, write_text_atomic
from .markers import (
    extract_section_content,
    has_any_agentsgen_markers,
    replace_section_content,
    validate_markers,
)
from .config import ToolConfig
from .model import ProjectInfo
from .normalize import normalize_markdown
from .shared_sections import render_all_shared
from .templates import prompt_template_path, templates_base_dir


@dataclass(frozen=True)
class FileResult:
    path: Path
    action: str  # created|updated|skipped|generated|error
    message: str = ""
    changed: bool = False
    diff: str = ""


def load_tool_config(target: Path) -> ToolConfig:
    cfg_path = target / CONFIG_FILENAME
    d = read_json(cfg_path)
    return ToolConfig.from_json(d)


def save_tool_config(target: Path, cfg: ToolConfig) -> None:
    cfg_path = target / CONFIG_FILENAME
    write_json_atomic(cfg_path, cfg.to_json())


def _unified_diff(path: Path, old: str, new: str) -> str:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=str(path),
            tofile=str(path),
        )
    )


def _patch_existing_with_generated(existing: str, generated: str, sections: list[str]) -> tuple[str, list[str]]:
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


def _render_shared_blocks(cfg: ToolConfig) -> dict[str, str]:
    ctx = {
        "project": cfg.project or {},
        "paths": cfg.paths or {},
        "commands": cfg.commands or {},
        "defaults": cfg.defaults or {},
    }
    return render_all_shared(ctx)


def _render_all(cfg: ToolConfig) -> tuple[str, str]:
    info = cfg.project_info
    base = templates_base_dir()
    agents_tpl, runbook_tpl = template_paths(base, info.stack)

    configs_hint = ", ".join([f"`{p}`" for p in info.config_locations]) if info.config_locations else "(not specified)"
    single_test_hint = (info.commands.get("single_test", "") or "(not specified)").strip()
    shared = _render_shared_blocks(cfg)

    agents_md = render_agents_md(
        info,
        agents_tpl,
        single_test_hint=single_test_hint,
        configs_hint=configs_hint,
        shared_blocks=shared,
    )
    runbook_md = render_runbook_md(info, runbook_tpl)

    return normalize_markdown(agents_md), normalize_markdown(runbook_md)


def _write_or_diff(path: Path, new_content: str, dry_run: bool, print_diff: bool) -> tuple[bool, str]:
    if path.exists():
        old = read_text(path)
        old_n = normalize_markdown(old)
        new_n = normalize_markdown(new_content)
        if old_n == new_n:
            return False, ""
        if dry_run:
            d = _unified_diff(path, old_n, new_n) if print_diff else ""
            return True, d
        write_text_atomic(path, new_n)
        d = _unified_diff(path, old_n, new_n) if print_diff else ""
        return True, d

    if dry_run:
        d = _unified_diff(path, "", new_content) if print_diff else ""
        return True, d
    write_text_atomic(path, new_content)
    d = _unified_diff(path, "", new_content) if print_diff else ""
    return True, d


def _handle_file(
    path: Path,
    generated_full: str,
    *,
    required: list[str],
    dry_run: bool,
    print_diff: bool,
) -> FileResult:
    # Three-mode behavior:
    # - missing file: create with markers
    # - has markers: patch by section ranges
    # - exists w/o markers: do not touch, create *.generated.md

    if not path.exists():
        changed, d = _write_or_diff(path, generated_full, dry_run=dry_run, print_diff=print_diff)
        return FileResult(path=path, action="created", message="created", changed=changed, diff=d)

    existing = read_text(path)
    if not has_any_agentsgen_markers(existing):
        gen_path = path.with_name(
            AGENTS_GENERATED_FILENAME if path.name == AGENTS_FILENAME else RUNBOOK_GENERATED_FILENAME
        )
        changed, d = _write_or_diff(gen_path, generated_full, dry_run=dry_run, print_diff=print_diff)
        return FileResult(
            path=gen_path,
            action="generated",
            message=f"{path.name} has no markers; wrote {gen_path.name} instead",
            changed=changed,
            diff=d,
        )

    problems = validate_markers(existing)
    if problems:
        msg = "; ".join([p.message for p in problems])
        return FileResult(path=path, action="error", message=msg)

    patched, missing = _patch_existing_with_generated(existing, generated_full, required)
    if missing:
        return FileResult(
            path=path,
            action="error",
            message=f"Missing required marker sections: {', '.join(missing)}",
        )

    changed, d = _write_or_diff(path, patched, dry_run=dry_run, print_diff=print_diff)
    return FileResult(path=path, action="updated" if changed else "skipped", message="updated" if changed else "no changes", changed=changed, diff=d)


def apply_config(
    target: Path,
    cfg: ToolConfig,
    *,
    write_prompts: bool,
    dry_run: bool,
    print_diff: bool,
) -> list[FileResult]:
    results: list[FileResult] = []

    agents_full, runbook_full = _render_all(cfg)

    results.append(
        _handle_file(
            target / AGENTS_FILENAME,
            agents_full,
            required=required_sections(cfg.project_info.stack),
            dry_run=dry_run,
            print_diff=print_diff,
        )
    )
    results.append(
        _handle_file(
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
        changed, d = _write_or_diff(prompt_path, prompt_content, dry_run=dry_run, print_diff=print_diff)
        results.append(
            FileResult(
                path=prompt_path,
                action="created" if not prompt_path.exists() else ("updated" if changed else "skipped"),
                message="prompt written" if changed else "prompt unchanged",
                changed=changed,
                diff=d,
            )
        )

    return results


def init_or_update(
    target: Path,
    info: ProjectInfo,
    write_prompts: bool,
    dry_run: bool,
    print_diff: bool,
) -> list[FileResult]:
    # Back-compat wrapper for older callers.
    cfg = ToolConfig.from_project_info(info.normalized())
    return apply_config(target, cfg, write_prompts=write_prompts, dry_run=dry_run, print_diff=print_diff)


def update_from_config(target: Path, dry_run: bool, print_diff: bool) -> list[FileResult]:
    tool_cfg = load_tool_config(target)
    return apply_config(target, tool_cfg, write_prompts=False, dry_run=dry_run, print_diff=print_diff)


def check_repo(target: Path) -> tuple[int, list[str], list[str]]:
    problems: list[str] = []
    warnings: list[str] = []
    cfg = target / CONFIG_FILENAME
    if not cfg.exists():
        problems.append(f"Missing {CONFIG_FILENAME}. Run: agentsgen init")
        return 2, problems, warnings

    tool_cfg = load_tool_config(target)
    info = tool_cfg.project_info

    for fname in [AGENTS_FILENAME, RUNBOOK_FILENAME]:
        p = target / fname
        if not p.exists():
            problems.append(f"Missing {fname}. Run: agentsgen init")
            continue

        text = read_text(p)
        if not has_any_agentsgen_markers(text):
            problems.append(f"{fname} has no AGENTSGEN markers (cannot update safely)")
            continue

        marker_problems = validate_markers(text)
        if marker_problems:
            for mp in marker_problems:
                problems.append(f"{fname}: {mp.message}")

        # Required sections must exist.
        required = required_sections(info.stack) if fname == AGENTS_FILENAME else required_runbook_sections()
        for sec in required:
            if extract_section_content(text, sec) is None:
                problems.append(f"{fname}: missing section markers for '{sec}'")
            else:
                body = (extract_section_content(text, sec) or "").strip()
                if not body:
                    problems.append(f"{fname}: section '{sec}' is empty")
                # Basic placeholder detection (cheap + useful).
                if body in ("- (not specified)", "- (none)", "- (no commands configured)", "- (not set)"):
                    warnings.append(
                        f"{fname}: section '{sec}' looks like a placeholder; fill it or remove the section"
                    )

    return (1 if problems else 0), problems, warnings
