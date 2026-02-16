from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

from .constants import (
    AGENTS_FILENAME,
    AGENTS_GENERATED_FILENAME,
    CONFIG_FILENAME,
    DEFAULT_PACK_FILES,
    DEFAULT_PACK_LLMS_FORMAT,
    DEFAULT_PACK_OUTPUT_DIR,
    PROMPTS_DIRNAME,
    RUNBOOK_FILENAME,
    RUNBOOK_GENERATED_FILENAME,
)
from .generate import (
    render_agents_md,
    render_runbook_md,
    required_sections,
    template_paths,
)
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
from .render import render_template, load_template
from .templates import pack_template_path


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


def _patch_existing_with_generated(
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

    configs_hint = (
        ", ".join([f"`{p}`" for p in info.config_locations])
        if info.config_locations
        else "(not specified)"
    )
    single_test_hint = (
        info.commands.get("single_test", "") or "(not specified)"
    ).strip()
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


def _write_or_diff(
    path: Path, new_content: str, dry_run: bool, print_diff: bool
) -> tuple[bool, str]:
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
        changed, d = _write_or_diff(
            path, generated_full, dry_run=dry_run, print_diff=print_diff
        )
        return FileResult(
            path=path, action="created", message="created", changed=changed, diff=d
        )

    existing = read_text(path)
    if not has_any_agentsgen_markers(existing):
        gen_path = _generated_sibling_path(path)
        changed, d = _write_or_diff(
            gen_path, generated_full, dry_run=dry_run, print_diff=print_diff
        )
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

    patched, missing = _patch_existing_with_generated(
        existing, generated_full, required
    )
    if missing:
        return FileResult(
            path=path,
            action="error",
            message=f"Missing required marker sections: {', '.join(missing)}",
        )

    changed, d = _write_or_diff(path, patched, dry_run=dry_run, print_diff=print_diff)
    return FileResult(
        path=path,
        action="updated" if changed else "skipped",
        message="updated" if changed else "no changes",
        changed=changed,
        diff=d,
    )


def _generated_sibling_path(path: Path) -> Path:
    if path.name == AGENTS_FILENAME:
        return path.with_name(AGENTS_GENERATED_FILENAME)
    if path.name == RUNBOOK_FILENAME:
        return path.with_name(RUNBOOK_GENERATED_FILENAME)
    return path.with_name(f"{path.stem}.generated{path.suffix}")


def _fmt_paths(items: list[str]) -> str:
    vals = [x.strip() for x in items if x and x.strip()]
    if not vals:
        return "(not detected)"
    return ", ".join([f"`{x}`" for x in vals])


def _pick_stack_for_pack(cfg: ToolConfig) -> tuple[str, str]:
    primary = str((cfg.project or {}).get("primary_stack", "")).strip().lower()
    if primary in ("python", "node", "static"):
        return primary, primary
    # For mixed/unknown we render via static templates with explicit placeholders.
    return "static", (primary or "mixed")


def _pack_command_value(cfg: ToolConfig, key: str, is_mixed: bool) -> str:
    if is_mixed:
        return "(mixed repo detected - set explicit command in .agentsgen.json)"
    v = str((cfg.commands or {}).get(key, "")).strip()
    if not v:
        v = str((cfg.project_info.commands or {}).get(key, "")).strip()
    return v or "(not detected)"


def _pack_notes(cfg: ToolConfig, stack_label: str) -> str:
    if stack_label == "mixed":
        return (
            "- Mixed repository detected.\n"
            "- Commands are intentionally conservative.\n"
            "- Configure explicit values in `.agentsgen.json` under `commands` and `pack`."
        )
    return "- Keep these files concise and command-accurate. Avoid speculative guidance."


def _render_pack_file(cfg: ToolConfig, stack_tpl: str, template_name: str) -> str:
    primary = str((cfg.project or {}).get("primary_stack", "")).strip().lower()
    is_mixed = primary not in ("python", "node", "static")
    project_name = str((cfg.project or {}).get("name", "")).strip() or cfg.project_info.project_name or "repository"

    paths = cfg.paths or {}
    output_dir = (cfg.pack.output_dir or DEFAULT_PACK_OUTPUT_DIR).strip()
    ctx = {
        "project_name": project_name,
        "stack": (primary or cfg.project_info.stack or "unknown"),
        "stack_label": primary or "mixed",
        "output_dir": output_dir,
        "source_dirs": _fmt_paths(list(paths.get("source_dirs", []) or [])),
        "config_locations": _fmt_paths(list(paths.get("config_locations", []) or [])),
        "docs_paths": _fmt_paths(list(paths.get("docs", []) or [])),
        "ci_location": str(paths.get("ci", ".github/workflows/") or ".github/workflows/"),
        "cmd_install": _pack_command_value(cfg, "install", is_mixed),
        "cmd_dev": _pack_command_value(cfg, "dev", is_mixed),
        "cmd_test": _pack_command_value(cfg, "test", is_mixed),
        "cmd_lint": _pack_command_value(cfg, "lint", is_mixed),
        "cmd_format": _pack_command_value(cfg, "format", is_mixed),
        "cmd_build": _pack_command_value(cfg, "build", is_mixed),
        "cmd_fast": _pack_command_value(cfg, "fast", is_mixed),
        "cmd_full": _pack_command_value(cfg, "full", is_mixed),
        "pack_notes": _pack_notes(cfg, primary or "mixed"),
    }

    tpl = pack_template_path(stack_tpl, template_name)
    return normalize_markdown(render_template(load_template(tpl), ctx))


def _pack_output_specs(cfg: ToolConfig) -> list[tuple[Path, str, list[str]]]:
    llms_format = (cfg.pack.llms_format or DEFAULT_PACK_LLMS_FORMAT).strip().lower()
    if llms_format not in ("txt", "md"):
        llms_format = DEFAULT_PACK_LLMS_FORMAT

    output_dir = Path((cfg.pack.output_dir or DEFAULT_PACK_OUTPUT_DIR).strip())
    stack_tpl, stack_label = _pick_stack_for_pack(cfg)
    _ = stack_label  # used by context generation from cfg.project.

    llms_name = "llms.txt" if llms_format == "txt" else "LLMS.md"
    llms_tpl = "llms.txt.tpl" if llms_format == "txt" else "LLMS.md.tpl"

    specs: list[tuple[Path, str, list[str]]] = [
        (Path(llms_name), llms_tpl, ["llms"]),
        (output_dir / "how-to-run.md", "how-to-run.md.tpl", ["how_to_run"]),
        (output_dir / "how-to-test.md", "how-to-test.md.tpl", ["how_to_test"]),
        (output_dir / "architecture.md", "architecture.md.tpl", ["architecture"]),
        (output_dir / "data-contracts.md", "data-contracts.md.tpl", ["data_contracts"]),
        (Path("SECURITY_AI.md"), "SECURITY_AI.md.tpl", ["security_ai"]),
        (Path("CONTRIBUTING_AI.md"), "CONTRIBUTING_AI.md.tpl", ["contributing_ai"]),
        (Path("README_SNIPPETS.md"), "README_SNIPPETS.md.tpl", ["readme_snippets"]),
    ]

    allow = [str(x).strip() for x in (cfg.pack.files or []) if str(x).strip()]
    if not allow:
        allow = list(DEFAULT_PACK_FILES)
    allow_set = {x.lower() for x in allow}

    filtered: list[tuple[Path, str, list[str]]] = []
    for rel_path, tpl_name, required in specs:
        key_path = str(rel_path).replace("\\", "/").lower()
        key_name = rel_path.name.lower()
        if key_path in allow_set or key_name in allow_set or ("llms" in allow_set and key_name in {"llms.txt", "llms.md"}):
            filtered.append((rel_path, tpl_name, required))

    # Always keep at least manifest file.
    if not filtered:
        filtered = [(Path(llms_name), llms_tpl, ["llms"])]

    rendered: list[tuple[Path, str, list[str]]] = []
    for rel_path, tpl_name, required in filtered:
        rendered.append((rel_path, _render_pack_file(cfg, stack_tpl, tpl_name), required))
    return rendered


def apply_pack(
    target: Path,
    cfg: ToolConfig,
    *,
    dry_run: bool,
    print_diff: bool,
) -> list[FileResult]:
    results: list[FileResult] = []
    if not cfg.pack.enabled:
        return [
            FileResult(
                path=target,
                action="skipped",
                message="pack.disabled in config",
                changed=False,
            )
        ]

    for rel_path, content, required in _pack_output_specs(cfg):
        out_path = (target / rel_path).resolve()
        target_resolved = target.resolve()
        if target_resolved not in out_path.parents and out_path != target_resolved:
            results.append(
                FileResult(
                    path=target / rel_path,
                    action="error",
                    message="pack output path escapes target directory",
                )
            )
            continue
        results.append(
            _handle_file(
                out_path,
                content,
                required=required,
                dry_run=dry_run,
                print_diff=print_diff,
            )
        )
    return results


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
        changed, d = _write_or_diff(
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
    return apply_config(
        target, cfg, write_prompts=write_prompts, dry_run=dry_run, print_diff=print_diff
    )


def update_from_config(
    target: Path, dry_run: bool, print_diff: bool
) -> list[FileResult]:
    tool_cfg = load_tool_config(target)
    return apply_config(
        target, tool_cfg, write_prompts=False, dry_run=dry_run, print_diff=print_diff
    )


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
        required = (
            required_sections(info.stack)
            if fname == AGENTS_FILENAME
            else required_runbook_sections()
        )
        for sec in required:
            if extract_section_content(text, sec) is None:
                problems.append(f"{fname}: missing section markers for '{sec}'")
            else:
                body = (extract_section_content(text, sec) or "").strip()
                if not body:
                    problems.append(f"{fname}: section '{sec}' is empty")
                # Basic placeholder detection (cheap + useful).
                if body in (
                    "- (not specified)",
                    "- (none)",
                    "- (no commands configured)",
                    "- (not set)",
                ):
                    warnings.append(
                        f"{fname}: section '{sec}' looks like a placeholder; fill it or remove the section"
                    )

    return (1 if problems else 0), problems, warnings
