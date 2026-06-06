from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .config import ToolConfig, merge_detect_hints
from .config_io import load_tool_config
from .constants import (
    AGENTS_FILENAME,
    CONFIG_FILENAME,
    DEFAULT_PACK_FILES,
    DEFAULT_PACK_LLMS_FORMAT,
    DEFAULT_PACK_OUTPUT_DIR,
    RUNBOOK_FILENAME,
)
from .generate import required_runbook_sections, required_sections
from .generated_artifacts import handle_generated_json_artifact
from .io_utils import read_json, read_text, write_text_atomic
from .markers import (
    count_agentsgen_marker_sections,
    extract_section_content,
    has_any_agentsgen_markers,
    validate_markers,
)
from .normalize import normalize_markdown
from .patch_engine import generated_sibling_path, handle_file, unified_diff
from .render import load_template, render_template
from .result_types import (
    AggregatedCheckReport,
    FileResult,
    ReadmeSnippet,
    ReadmeSnippetsReport,
    RepoStatusReport,
    StatusFileReport,
)
from .site_pack import build_site_llms_manifest
from .templates import pack_template_path
from .validators import (
    validate_aggregated_check_payload,
    validate_entrypoints_payload,
    validate_id_context_payload,
    validate_repo_status_payload,
)

_SNIPPET_START_RE = re.compile(
    r"<!--\s*AGENTSGEN:SNIPPET\s+name=([a-zA-Z0-9_\-]+)\s*-->"
)
_SNIPPET_END_RE = re.compile(r"<!--\s*AGENTSGEN:ENDSNIPPET\s*-->")


def _extract_readme_snippets(readme_text: str) -> list[ReadmeSnippet]:
    snippets: list[ReadmeSnippet] = []
    seen: set[str] = set()
    active_name: str | None = None
    active_start_line: int | None = None
    active_lines: list[str] = []

    for line_no, line in enumerate(readme_text.splitlines(keepends=True), start=1):
        start_m = _SNIPPET_START_RE.fullmatch(line.strip())
        end_m = _SNIPPET_END_RE.fullmatch(line.strip())

        if start_m:
            if active_name is not None:
                raise ValueError(
                    f"Nested snippet '{start_m.group(1)}' inside '{active_name}' is not allowed (line {line_no})."
                )
            name = start_m.group(1)
            if name in seen:
                raise ValueError(f"Duplicate snippet name '{name}' (line {line_no}).")
            seen.add(name)
            active_name = name
            active_start_line = line_no
            active_lines = []
            continue

        if end_m:
            if active_name is None:
                raise ValueError(f"ENDSNIPPET without matching start (line {line_no}).")
            snippets.append(
                ReadmeSnippet(
                    name=active_name,
                    start_line=active_start_line or line_no,
                    end_line=line_no,
                    content="".join(active_lines),
                )
            )
            active_name = None
            active_start_line = None
            active_lines = []
            continue

        if active_name is not None:
            active_lines.append(line)

    if active_name is not None:
        raise ValueError(
            f"Snippet '{active_name}' starting on line {active_start_line} has no matching ENDSNIPPET."
        )

    return snippets


def _render_readme_snippets(snippets: list[ReadmeSnippet], source_name: str) -> str:
    toc = "\n".join(f"- [{s.name}](#{s.name})" for s in snippets)
    parts = [
        "# README Snippets (generated)",
        "",
        "This file is generated from README.md snippet markers. Do not edit by hand.",
        "",
        "## Contents",
        toc,
    ]
    for snippet in snippets:
        parts.extend(
            [
                "",
                f"## {snippet.name}",
                "",
                f"Source: {source_name} (snippet: {snippet.name})",
                "",
                snippet.content.rstrip("\n"),
            ]
        )
    return "\n".join(parts).rstrip() + "\n"


def generate_readme_snippets(
    target: Path,
    *,
    readme_path: Path,
    output_path: Path,
    check: bool,
    dry_run: bool,
    print_diff: bool,
) -> ReadmeSnippetsReport:
    del target
    try:
        readme_text = read_text(readme_path)
        snippets = _extract_readme_snippets(readme_text)
    except Exception as exc:
        return ReadmeSnippetsReport(
            status="error",
            check=check,
            dry_run=dry_run,
            format_version=1,
            readme_path=str(readme_path),
            output_path=str(output_path),
            snippets_count=0,
            snippets=[],
            message=str(exc),
        )

    if not snippets:
        diff = ""
        status = "ok"
        message = "no snippets found"
        if check and output_path.exists():
            status = "drift"
            if print_diff:
                diff = unified_diff(output_path, read_text(output_path), "")
        return ReadmeSnippetsReport(
            status=status,
            check=check,
            dry_run=dry_run,
            format_version=1,
            readme_path=str(readme_path),
            output_path=str(output_path),
            snippets_count=0,
            snippets=[],
            diff=diff,
            message=message,
        )

    new_content = _render_readme_snippets(snippets, readme_path.name)
    diff = ""
    status = "ok"

    if output_path.exists():
        current = read_text(output_path)
        if current != new_content:
            status = "drift" if check else "ok"
            if print_diff:
                diff = unified_diff(output_path, current, new_content)
            if not check and not dry_run:
                write_text_atomic(output_path, new_content)
    else:
        if check:
            status = "drift"
            if print_diff:
                diff = unified_diff(output_path, "", new_content)
        elif not dry_run:
            write_text_atomic(output_path, new_content)
        elif print_diff:
            diff = unified_diff(output_path, "", new_content)

    return ReadmeSnippetsReport(
        status=status,
        check=check,
        dry_run=dry_run,
        format_version=1,
        readme_path=str(readme_path),
        output_path=str(output_path),
        snippets_count=len(snippets),
        snippets=snippets,
        diff=diff,
    )


def _fmt_paths(items: list[str]) -> str:
    vals = [x.strip() for x in items if x and x.strip()]
    if not vals:
        return "(not detected)"
    return ", ".join([f"`{x}`" for x in vals])


def _pick_stack_for_pack(cfg: ToolConfig) -> tuple[str, str]:
    primary = str((cfg.project or {}).get("primary_stack", "")).strip().lower()
    if primary in ("python", "node", "static"):
        return primary, primary
    return "static", (primary or "mixed")


def _pack_command_value(cfg: ToolConfig, key: str, is_mixed: bool) -> str:
    if is_mixed:
        return "(mixed repo detected - set explicit command in .agentsgen.json)"
    value = str((cfg.commands or {}).get(key, "")).strip()
    if not value:
        value = str((cfg.project_info.commands or {}).get(key, "")).strip()
    return value or "(not detected)"


def _pack_notes(cfg: ToolConfig, stack_label: str) -> str:
    del cfg
    if stack_label == "mixed":
        return (
            "- Mixed repository detected.\n"
            "- Commands are intentionally conservative.\n"
            "- Configure explicit values in `.agentsgen.json` under `commands` and `pack`."
        )
    return (
        "- Keep these files concise and command-accurate. Avoid speculative guidance."
    )


def _entrypoint_title(command_id: str) -> str:
    labels = {
        "install": "Install",
        "dev": "Dev",
        "test": "Test",
        "lint": "Lint",
        "build": "Build",
        "format": "Format",
        "typecheck": "Typecheck",
        "run": "Run",
    }
    return labels.get(
        command_id, command_id.replace("_", " ").replace("-", " ").title()
    )


def _entrypoint_source_for_command(
    command_id: str,
    command: str,
    *,
    explicit: bool,
    evidence: dict[str, object],
) -> dict[str, str]:
    if explicit:
        return {"kind": "config", "hint": f".agentsgen.json:commands.{command_id}"}
    cmd = command.strip()
    if cmd.startswith("make "):
        target = cmd.split(maxsplit=1)[1].strip() if " " in cmd else ""
        return {"kind": "makefile", "hint": target or "Makefile"}
    if any(token in cmd for token in ("npm ", "pnpm ", "yarn ")):
        hint = ""
        if " run " in cmd:
            hint = cmd.split(" run ", 1)[1].split()[0]
        elif " test" in cmd:
            hint = "test"
        elif " install" in cmd:
            hint = "install"
        return {"kind": "package.json", "hint": hint}
    python_evidence = [str(x) for x in (evidence.get("python") or [])]
    if cmd.startswith(("uv ", "poetry ", "python ", "python3 ")):
        hint = next((x for x in python_evidence if "pyproject.toml" in x), "")
        return {"kind": "pyproject", "hint": hint}
    return {"kind": "detected", "hint": ""}


def _stable_payload_without_timestamp(payload: dict[str, object]) -> str:
    clone = json.loads(json.dumps(payload))
    clone["generated_at"] = ""
    return json.dumps(clone, sort_keys=True, separators=(",", ":"))


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _pack_entrypoints_json(target: Path, cfg: ToolConfig, *, autodetect: bool) -> str:
    config_commands: dict[str, object] = {}
    if (target / CONFIG_FILENAME).exists():
        try:
            config_commands = load_tool_config(target).commands
        except Exception:
            config_commands = {}
    detected_commands = dict(cfg.commands or {})
    stack = (
        str((cfg.project or {}).get("primary_stack", "")).strip().lower()
        or str(cfg.project_info.stack or "").strip().lower()
        or "unknown"
    )
    if stack not in {"python", "node", "static", "mixed", "unknown"}:
        stack = "unknown"
    stable_ids = [
        "install",
        "dev",
        "test",
        "lint",
        "build",
        "format",
        "typecheck",
        "run",
    ]
    extra_ids = [
        key
        for key in sorted(config_commands.keys())
        if key not in stable_ids and str(config_commands.get(key, "")).strip()
    ]
    commands: list[dict[str, object]] = []
    evidence = dict(cfg.evidence or {})
    for command_id in stable_ids + extra_ids:
        explicit_command = str(config_commands.get(command_id, "") or "").strip()
        detected_command = str(detected_commands.get(command_id, "") or "").strip()
        command = explicit_command or detected_command
        if not command:
            continue
        commands.append(
            {
                "id": command_id,
                "title": _entrypoint_title(command_id),
                "command": command,
                "cwd": ".",
                "source": _entrypoint_source_for_command(
                    command_id,
                    command,
                    explicit=bool(explicit_command),
                    evidence=evidence,
                ),
                "notes": "",
            }
        )
    payload: dict[str, object] = {
        "version": 1,
        "generated_by": "agentsgen",
        "generated_at": "",
        "repo": {"path": ".", "stack": stack, "autodetect": autodetect},
        "commands": commands,
    }
    existing_path = target / "agents.entrypoints.json"
    if existing_path.exists():
        try:
            existing = read_json(existing_path)
            if str(
                existing.get("generated_by", "")
            ) == "agentsgen" and _stable_payload_without_timestamp(
                existing
            ) == _stable_payload_without_timestamp(payload):
                payload["generated_at"] = str(existing.get("generated_at", "") or "")
            else:
                payload["generated_at"] = _utc_now_iso()
        except Exception:
            payload["generated_at"] = _utc_now_iso()
    else:
        payload["generated_at"] = _utc_now_iso()
    validate_entrypoints_payload(payload)
    return json.dumps(payload, indent=2) + "\n"


def _pack_id_context_json(target: Path, cfg: ToolConfig, *, autodetect: bool) -> str:
    project_name = (
        str((cfg.project or {}).get("name", "")).strip()
        or cfg.project_info.project_name
        or target.name
    )
    stack = (
        str((cfg.project or {}).get("primary_stack", "")).strip().lower()
        or str(cfg.project_info.stack or "").strip().lower()
        or "unknown"
    )
    if stack not in {"python", "node", "static", "mixed", "unknown"}:
        stack = "unknown"
    output_dir = Path((cfg.pack.output_dir or DEFAULT_PACK_OUTPUT_DIR).strip())
    llms_format = (cfg.pack.llms_format or DEFAULT_PACK_LLMS_FORMAT).strip().lower()
    if llms_format not in {"txt", "md"}:
        llms_format = DEFAULT_PACK_LLMS_FORMAT
    llms_name = "llms.txt" if llms_format == "txt" else "LLMS.md"
    id_context_path = str(output_dir / "id-context.json").replace("\\", "/")
    payload: dict[str, object] = {
        "version": 1,
        "generated_by": "agentsgen",
        "generated_at": "",
        "repo": {
            "name": project_name,
            "path": ".",
            "stack": stack,
            "autodetect": autodetect,
        },
        "handoff": {
            "consumer": "ID",
            "target": "agentsmd",
            "status": "ready",
            "purpose": "repo-scoped handoff surface for ID-compatible human-AI workflows",
        },
        "bundle": {
            "repo_docs": {"agents_md": AGENTS_FILENAME, "runbook_md": RUNBOOK_FILENAME},
            "pack": {
                "llms": llms_name,
                "entrypoints": "agents.entrypoints.json",
                "id_context": id_context_path,
                "how_to_run": str(output_dir / "how-to-run.md").replace("\\", "/"),
                "how_to_test": str(output_dir / "how-to-test.md").replace("\\", "/"),
                "architecture": str(output_dir / "architecture.md").replace("\\", "/"),
                "data_contracts": str(output_dir / "data-contracts.md").replace(
                    "\\", "/"
                ),
                "security": "SECURITY_AI.md",
                "contributing": "CONTRIBUTING_AI.md",
                "readme_snippets": "README_SNIPPETS.md",
            },
            "optional_repo_artifacts": {
                "repomap": str(output_dir / "repomap.md").replace("\\", "/"),
                "repomap_compact": str(output_dir / "repomap.compact.md").replace(
                    "\\", "/"
                ),
                "graph": str(output_dir / "graph.mmd").replace("\\", "/"),
                "knowledge": "agents.knowledge.json",
                "proof_tasks_dir": str(output_dir / "tasks").replace("\\", "/"),
            },
        },
        "usage": {
            "preferred_inputs": [
                AGENTS_FILENAME,
                RUNBOOK_FILENAME,
                "agents.entrypoints.json",
                str(output_dir / "how-to-run.md").replace("\\", "/"),
                str(output_dir / "how-to-test.md").replace("\\", "/"),
                str(output_dir / "architecture.md").replace("\\", "/"),
                str(output_dir / "data-contracts.md").replace("\\", "/"),
            ],
            "notes": [
                "Use this manifest as the repo-local companion to an ID profile; it does not replace human-owned ID artifacts.",
                "AGENTS.md Generator owns repo context, while ID owns portable person and policy context.",
                "SET can route both layers together, but this manifest is useful even without SET.",
            ],
        },
    }
    existing_path = target / output_dir / "id-context.json"
    if existing_path.exists():
        try:
            existing = read_json(existing_path)
            if str(
                existing.get("generated_by", "")
            ) == "agentsgen" and _stable_payload_without_timestamp(
                existing
            ) == _stable_payload_without_timestamp(payload):
                payload["generated_at"] = str(existing.get("generated_at", "") or "")
            else:
                payload["generated_at"] = _utc_now_iso()
        except Exception:
            payload["generated_at"] = _utc_now_iso()
    else:
        payload["generated_at"] = _utc_now_iso()
    validate_id_context_payload(payload)
    return json.dumps(payload, indent=2) + "\n"


_handle_generated_json_file = handle_generated_json_artifact


def _render_pack_file(cfg: ToolConfig, stack_tpl: str, template_name: str) -> str:
    primary = str((cfg.project or {}).get("primary_stack", "")).strip().lower()
    is_mixed = primary not in ("python", "node", "static")
    project_name = (
        str((cfg.project or {}).get("name", "")).strip()
        or cfg.project_info.project_name
        or "repository"
    )
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
        "ci_location": str(
            paths.get("ci", ".github/workflows/") or ".github/workflows/"
        ),
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


def _resolve_target_child(target: Path, rel_path: Path) -> Path | None:
    target_resolved = target.resolve()
    out_path = (target / rel_path).resolve()
    if target_resolved not in out_path.parents and out_path != target_resolved:
        return None
    return out_path


def _pack_output_specs(
    target: Path,
    cfg: ToolConfig,
    *,
    autodetect: bool,
    site_url: str | None = None,
    site_manifest_builder: Callable[[str], str] | None = None,
) -> list[tuple[Path, str, list[str]]]:
    llms_format = (cfg.pack.llms_format or DEFAULT_PACK_LLMS_FORMAT).strip().lower()
    if llms_format not in ("txt", "md"):
        llms_format = DEFAULT_PACK_LLMS_FORMAT
    output_dir = Path((cfg.pack.output_dir or DEFAULT_PACK_OUTPUT_DIR).strip())
    stack_tpl, _stack_label = _pick_stack_for_pack(cfg)
    llms_name = "llms.txt" if llms_format == "txt" else "LLMS.md"
    llms_tpl = "llms.txt.tpl" if llms_format == "txt" else "LLMS.md.tpl"
    specs: list[tuple[Path, str, list[str]]] = [
        (Path(llms_name), llms_tpl, ["llms"]),
        (Path("agents.entrypoints.json"), "__generated_entrypoints_json__", []),
        (output_dir / "id-context.json", "__generated_id_context_json__", []),
        (output_dir / "how-to-run.md", "how-to-run.md.tpl", ["how_to_run"]),
        (output_dir / "how-to-test.md", "how-to-test.md.tpl", ["how_to_test"]),
        (output_dir / "architecture.md", "architecture.md.tpl", ["architecture"]),
        (output_dir / "data-contracts.md", "data-contracts.md.tpl", ["data_contracts"]),
        (Path("SECURITY_AI.md"), "SECURITY_AI.md.tpl", ["security_ai"]),
        (Path("CONTRIBUTING_AI.md"), "CONTRIBUTING_AI.md.tpl", ["contributing_ai"]),
        (Path("README_SNIPPETS.md"), "README_SNIPPETS.md.tpl", ["readme_snippets"]),
    ]
    allow = [str(x).strip() for x in (cfg.pack.files or []) if str(x).strip()] or list(
        DEFAULT_PACK_FILES
    )
    allow_set = {x.lower() for x in allow}
    filtered: list[tuple[Path, str, list[str]]] = []
    for rel_path, tpl_name, required in specs:
        key_path = str(rel_path).replace("\\", "/").lower()
        key_name = rel_path.name.lower()
        if (
            key_path in allow_set
            or key_name in allow_set
            or ("entrypoints" in allow_set and key_name == "agents.entrypoints.json")
            or ("id-context" in allow_set and key_name == "id-context.json")
            or ("llms" in allow_set and key_name in {"llms.txt", "llms.md"})
        ):
            filtered.append((rel_path, tpl_name, required))
    if not filtered:
        filtered = [(Path(llms_name), llms_tpl, ["llms"])]
    rendered: list[tuple[Path, str, list[str]]] = []
    manifest_builder = site_manifest_builder or build_site_llms_manifest
    for rel_path, tpl_name, required in filtered:
        if site_url and rel_path.name.lower() in {"llms.txt", "llms.md"}:
            rendered.append((rel_path, manifest_builder(site_url), required))
        elif tpl_name == "__generated_entrypoints_json__":
            rendered.append(
                (
                    rel_path,
                    _pack_entrypoints_json(target, cfg, autodetect=autodetect),
                    required,
                )
            )
        elif tpl_name == "__generated_id_context_json__":
            rendered.append(
                (
                    rel_path,
                    _pack_id_context_json(target, cfg, autodetect=autodetect),
                    required,
                )
            )
        else:
            rendered.append(
                (rel_path, _render_pack_file(cfg, stack_tpl, tpl_name), required)
            )
    return rendered


def pack_plan_specs(
    target: Path,
    cfg: ToolConfig,
    *,
    autodetect: bool,
    site_url: str | None = None,
    site_manifest_builder: Callable[[str], str] | None = None,
) -> list[tuple[Path, list[str]]]:
    specs = _pack_output_specs(
        target,
        cfg,
        autodetect=autodetect,
        site_url=site_url,
        site_manifest_builder=site_manifest_builder,
    )
    return sorted(
        [(rel_path, list(required)) for rel_path, _content, required in specs],
        key=lambda item: str(item[0]).replace("\\", "/"),
    )


def apply_pack(
    target: Path,
    cfg: ToolConfig,
    *,
    autodetect: bool,
    site_url: str | None = None,
    site_manifest_builder: Callable[[str], str] | None = None,
    dry_run: bool,
    print_diff: bool,
) -> list[FileResult]:
    if not cfg.pack.enabled:
        return [
            FileResult(
                path=target,
                action="skipped",
                message="pack.disabled in config",
                changed=False,
            )
        ]
    results: list[FileResult] = []
    for rel_path, content, required in _pack_output_specs(
        target,
        cfg,
        autodetect=autodetect,
        site_url=site_url,
        site_manifest_builder=site_manifest_builder,
    ):
        out_path = _resolve_target_child(target, rel_path)
        if out_path is None:
            results.append(
                FileResult(
                    path=target / rel_path,
                    action="error",
                    message="pack output path escapes target directory",
                )
            )
            continue
        if rel_path.suffix == ".json":
            results.append(
                handle_generated_json_artifact(
                    out_path, content, dry_run=dry_run, print_diff=print_diff
                )
            )
        else:
            results.append(
                handle_file(
                    out_path,
                    content,
                    required=required,
                    dry_run=dry_run,
                    print_diff=print_diff,
                )
            )
    return results


def check_repo(target: Path) -> tuple[int, list[str], list[str]]:
    problems: list[str] = []
    warnings: list[str] = []
    cfg = target / CONFIG_FILENAME
    if not cfg.exists():
        problems.append(f"Missing {CONFIG_FILENAME}. Run: agentsgen init")
        return 2, problems, warnings
    try:
        tool_cfg = load_tool_config(target)
    except Exception as exc:
        problems.append(f"Invalid {CONFIG_FILENAME}: {exc}")
        return 2, problems, warnings
    info = tool_cfg.project_info
    for fname in [AGENTS_FILENAME, RUNBOOK_FILENAME]:
        path = target / fname
        if not path.exists():
            problems.append(f"Missing {fname}. Run: agentsgen init")
            continue
        try:
            text = read_text(path)
        except Exception as exc:
            problems.append(f"{fname}: unreadable ({exc})")
            continue
        if not has_any_agentsgen_markers(text):
            problems.append(f"{fname} has no AGENTSGEN markers (cannot update safely)")
            continue
        for marker_problem in validate_markers(text):
            problems.append(f"{fname}: {marker_problem.message}")
        required = (
            required_sections(info.stack)
            if fname == AGENTS_FILENAME
            else required_runbook_sections()
        )
        for sec in required:
            body = extract_section_content(text, sec)
            if body is None:
                problems.append(f"{fname}: missing section markers for '{sec}'")
            elif not body.strip():
                problems.append(f"{fname}: section '{sec}' is empty")
            elif body.strip() in (
                "- (not specified)",
                "- (none)",
                "- (no commands configured)",
                "- (not set)",
            ):
                warnings.append(
                    f"{fname}: section '{sec}' looks like a placeholder; fill it or remove the section"
                )
    return (1 if problems else 0), problems, warnings


def run_core_check(target: Path) -> dict[str, object]:
    code, problems, warnings = check_repo(target)
    status = "error" if code == 2 else ("drift" if code == 1 else "ok")
    return {
        "status": status,
        "drift_count": len(problems) if status == "drift" else 0,
        "error_count": len(problems) if status == "error" else 0,
        "warnings_count": len(warnings),
        "results": [{"level": "problem", "message": item} for item in problems]
        + [{"level": "warning", "message": item} for item in warnings],
        "raw": {
            "exit_code": code,
            "problems": list(problems),
            "warnings": list(warnings),
        },
    }


def run_pack_check(target: Path) -> dict[str, object]:
    try:
        from .detect import detect_repo

        cfg_path = target / CONFIG_FILENAME
        cfg = load_tool_config(target) if cfg_path.exists() else ToolConfig()
        det_cfg = ToolConfig.from_detect(detect_repo(target))
        existing_pack = cfg.pack
        cfg = merge_detect_hints(cfg, det_cfg)
        cfg.pack = existing_pack
        results = apply_pack(
            target, cfg, autodetect=True, dry_run=True, print_diff=False
        )
    except Exception as exc:
        return {
            "status": "error",
            "drift_count": 0,
            "error_count": 1,
            "raw": {"status": "error", "summary": f"pack:error ({exc})", "results": []},
            "reason": str(exc),
        }
    errors = [r for r in results if r.action == "error"]
    drift_results = [
        r
        for r in results
        if r.action in ("created", "updated", "generated") and r.changed
    ]
    status = "error" if errors else ("drift" if drift_results else "ok")
    return {
        "status": status,
        "drift_count": len(drift_results),
        "error_count": len(errors),
        "raw": {
            "status": status,
            "summary": f"pack:{status} (created={sum(1 for r in results if r.action == 'created')}, updated={sum(1 for r in results if r.action == 'updated')}, generated={sum(1 for r in results if r.action == 'generated')}, errors={len(errors)})",
            "check": True,
            "dry_run": True,
            "results": [
                {
                    "path": str(r.path),
                    "action": r.action,
                    "message": r.message,
                    "changed": bool(r.changed),
                    "diff": r.diff or "",
                }
                for r in results
            ],
        },
    }


def run_snippets_check(target: Path) -> dict[str, object]:
    report = generate_readme_snippets(
        target,
        readme_path=target / "README.md",
        output_path=target / "README_SNIPPETS.generated.md",
        check=True,
        dry_run=True,
        print_diff=False,
    )
    return {
        "status": report.status,
        "drift_count": 1 if report.status == "drift" else 0,
        "error_count": 1 if report.status == "error" else 0,
        "raw": report.to_json(),
    }


def aggregate_check(
    target: Path,
    *,
    pack_check: bool,
    snippets_check: bool,
) -> AggregatedCheckReport:
    checks: dict[str, object] = {
        "core": run_core_check(target),
        "pack": None,
        "snippets": None,
    }
    if pack_check:
        checks["pack"] = run_pack_check(target)
    if snippets_check:
        checks["snippets"] = run_snippets_check(target)
    enabled_checks = [checks["core"]] + [
        checks[name] for name in ("pack", "snippets") if checks[name] is not None
    ]
    statuses = [
        str(block.get("status", "ok"))
        for block in enabled_checks
        if isinstance(block, dict)
    ]
    summary = {"ok": True, "drift_count": 0, "error_count": 0, "skipped_count": 0}
    for block in enabled_checks:
        if not isinstance(block, dict):
            continue
        status = str(block.get("status", "ok"))
        summary["drift_count"] += int(block.get("drift_count", 0))
        summary["error_count"] += int(block.get("error_count", 0))
        if status == "skipped":
            summary["skipped_count"] += 1
    overall = (
        "error" if "error" in statuses else ("drift" if "drift" in statuses else "ok")
    )
    summary["ok"] = overall == "ok"
    report = AggregatedCheckReport(
        version=1,
        command="check",
        path=str(target.resolve()),
        status=overall,
        checks=checks,
        summary=summary,
    )
    validate_aggregated_check_payload(report.to_json())
    return report


def _status_for_file(
    path: Path, *, generated_suffix: str
) -> tuple[StatusFileReport, list[str], list[str]]:
    findings: list[str] = []
    errors: list[str] = []
    generated = generated_sibling_path(path, generated_suffix).exists()
    if not path.exists():
        findings.append(f"Missing {path.name}")
        return StatusFileReport(False, False, 0, generated), findings, errors
    try:
        text = read_text(path)
    except Exception as exc:
        errors.append(f"Unreadable {path.name}: {exc}")
        return StatusFileReport(True, False, 0, generated), findings, errors
    markers_found = has_any_agentsgen_markers(text)
    marker_sections = count_agentsgen_marker_sections(text) if markers_found else 0
    if not markers_found:
        findings.append(
            f"{path.name} has no AGENTSGEN markers (updates will go to generated siblings)"
        )
    else:
        for marker_problem in validate_markers(text):
            errors.append(f"{path.name}: {marker_problem.message}")
    if generated:
        findings.append(
            f"Generated sibling exists for {path.name}: {generated_sibling_path(path, generated_suffix).name}"
        )
    return (
        StatusFileReport(True, markers_found, marker_sections, generated),
        findings,
        errors,
    )


def status_repo(target: Path) -> RepoStatusReport:
    findings: list[str] = []
    errors: list[str] = []
    target = target.resolve()
    cfg_path = target / CONFIG_FILENAME
    generated_suffix = ".generated"
    tool_cfg: ToolConfig | None = None
    if not cfg_path.exists():
        findings.append(f"Missing {CONFIG_FILENAME}")
        config = {"present": False}
    else:
        config = {"present": True}
        try:
            tool_cfg = load_tool_config(target)
            generated_suffix = tool_cfg.generated_suffix or ".generated"
        except Exception as exc:
            errors.append(f"Invalid {CONFIG_FILENAME}: {exc}")
    agents_report, agent_findings, agent_errors = _status_for_file(
        target / AGENTS_FILENAME, generated_suffix=generated_suffix
    )
    runbook_report, runbook_findings, runbook_errors = _status_for_file(
        target / RUNBOOK_FILENAME, generated_suffix=generated_suffix
    )
    findings.extend(agent_findings)
    findings.extend(runbook_findings)
    errors.extend(agent_errors)
    errors.extend(runbook_errors)
    generated_files = sorted(
        str(p.relative_to(target)) for p in target.rglob(f"*{generated_suffix}.*")
    )
    pack_findings: list[str] = []
    pack_errors: list[str] = []
    pack_status = "skipped" if tool_cfg is None and not cfg_path.exists() else "ok"
    if tool_cfg is not None:
        try:
            specs = _pack_output_specs(target, tool_cfg, autodetect=False)
            for rel_path, _content, _required in specs:
                path = _resolve_target_child(target, rel_path)
                if path is None:
                    pack_errors.append(
                        f"Pack output path escapes target directory: {rel_path.as_posix()}"
                    )
                    continue
                if not path.exists():
                    pack_findings.append(f"Missing pack file: {rel_path.as_posix()}")
                    continue
                try:
                    text = read_text(path)
                except Exception as exc:
                    pack_errors.append(
                        f"Unreadable pack file {rel_path.as_posix()}: {exc}"
                    )
                    continue
                if not has_any_agentsgen_markers(text):
                    pack_findings.append(
                        f"Pack file has no AGENTSGEN markers: {rel_path.as_posix()}"
                    )
                else:
                    for marker_problem in validate_markers(text):
                        pack_errors.append(
                            f"{rel_path.as_posix()}: {marker_problem.message}"
                        )
                gen_path = generated_sibling_path(path, generated_suffix)
                if gen_path.exists():
                    pack_findings.append(
                        f"Generated sibling exists for pack file: {gen_path.relative_to(target).as_posix()}"
                    )
        except Exception as exc:
            pack_errors.append(f"Pack status error: {exc}")
    if pack_errors:
        pack_status = "error"
    elif pack_findings:
        pack_status = "drift"
    elif tool_cfg is not None:
        pack_status = "ok"
    if generated_files:
        findings.append(f"Generated fallback files present: {len(generated_files)}")
    report = RepoStatusReport(
        status="error"
        if (len(errors) + len(pack_errors))
        else ("drift" if (len(findings) + len(pack_findings)) else "ok"),
        path=str(target),
        config=config,
        agents_md=agents_report,
        runbook_md=runbook_report,
        pack={"status": pack_status, "findings": pack_findings, "errors": pack_errors},
        generated={"count": len(generated_files), "files": generated_files},
        summary={
            "drift": len(findings) + len(pack_findings),
            "errors": len(errors) + len(pack_errors),
        },
    )
    validate_repo_status_payload(report.to_json())
    return report
