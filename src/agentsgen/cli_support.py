from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .config import ToolConfig
from .detect import detect_repo
from .pack_engine import pack_plan_specs
from .stacks import adapter_for
from .stacks.base import project_name_from_dir

console = Console(stderr=False)
err_console = Console(stderr=True)


def parse_csv(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x and x.strip()]


def resolve_repo_file(target: Path, supplied: Path | None, default_name: str) -> Path:
    if supplied is None:
        return target / default_name
    return supplied if supplied.is_absolute() else target / supplied


def print_results(results, print_diff: bool) -> None:
    table = Table(title="agentsgen")
    table.add_column("Action", style="bold")
    table.add_column("Path")
    table.add_column("Message")
    for row in results:
        table.add_row(row.action, str(row.path), row.message)
    console.print(table)
    if print_diff:
        for row in results:
            if row.diff:
                console.print(row.diff)


def results_payload(results) -> list[dict[str, object]]:
    return [
        {
            "path": str(r.path),
            "action": r.action,
            "message": r.message,
            "changed": bool(r.changed),
            "diff": r.diff or "",
        }
        for r in results
    ]


def path_relative_to_target(path: Path, target: Path) -> str:
    try:
        return str(path.resolve().relative_to(target.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def pack_plan_payload(
    *,
    target: Path,
    cfg: ToolConfig,
    autodetect: bool,
    results,
) -> list[dict[str, object]]:
    sections_map: dict[str, list[str]] = {
        str(rel).replace("\\", "/"): sections
        for rel, sections in pack_plan_specs(target, cfg, autodetect=autodetect)
    }
    rows: list[dict[str, object]] = []
    for row in results:
        if row.action not in ("created", "updated", "generated"):
            continue
        rel = path_relative_to_target(row.path, target)
        action = {"created": "create", "updated": "update", "generated": "generate"}[
            row.action
        ]
        rows.append(
            {
                "path": rel,
                "action": action,
                "sections": list(sections_map.get(rel, [])),
                "message": row.message,
            }
        )
    return sorted(rows, key=lambda x: str(x["path"]))


def print_pack_plan(plan: list[dict[str, object]]) -> None:
    table = Table(title="pack plan")
    table.add_column("Action", style="bold")
    table.add_column("Path")
    table.add_column("Sections")
    if not plan:
        table.add_row("none", "-", "-")
    else:
        for row in plan:
            sections = ", ".join([str(x) for x in (row.get("sections") or [])]) or "-"
            table.add_row(str(row["action"]), str(row["path"]), sections)
    console.print(table)


def print_pack_plan_header(
    *,
    target: Path,
    autodetect: bool,
    output_dir: str,
    files_count: int,
) -> None:
    console.print(f"repo: {target.resolve()}")
    console.print(f"autodetect: {'on' if autodetect else 'off'}")
    console.print(f"output_dir: {output_dir}")
    console.print(f"files_count: {files_count}")


def interactive_init(
    target: Path,
    defaults: bool,
    stack_opt: str | None,
    name_opt: str | None,
):
    det = detect_repo(target)
    suggested = str(det.project.get("primary_stack", "static"))
    confidence = (
        "high"
        if (det.evidence.python or det.evidence.node or det.evidence.make)
        else "low"
    )
    if suggested == "mixed":
        suggested = "static"
    if defaults:
        stack = (stack_opt or suggested).strip().lower()
        project_name = (name_opt or project_name_from_dir(target)).strip()
    else:
        stack = (
            typer.prompt(
                f"Stack (node|python|static) [detected: {suggested}, {confidence}]",
                default=(stack_opt or suggested),
            )
            .strip()
            .lower()
        )
        project_name = typer.prompt(
            "Project name",
            default=(name_opt or project_name_from_dir(target)),
        ).strip()
    adapter = adapter_for(stack)
    info = adapter.default_info(target, project_name)
    if defaults:
        return info

    def req(label: str, key: str, default: str) -> str:
        val = typer.prompt(label, default=default).strip()
        if not val:
            raise typer.BadParameter(f"{label} cannot be empty")
        info.commands[key] = val
        return val

    def opt(label: str, key: str, default: str) -> None:
        val = typer.prompt(label, default=default, show_default=True).strip()
        if val:
            info.commands[key] = val

    if stack == "node":
        info.package_manager = typer.prompt(
            "Package manager (npm|pnpm|yarn)", default=info.package_manager or "npm"
        ).strip()
    if stack == "python":
        info.python_tooling = typer.prompt(
            "Python tooling (venv|poetry)", default=info.python_tooling or "venv"
        ).strip()
    req("Install command", "install", info.commands.get("install", ""))
    req("Dev command", "dev", info.commands.get("dev", ""))
    req("Test command", "test", info.commands.get("test", ""))
    opt("Lint command (optional)", "lint", info.commands.get("lint", ""))
    opt("Format command (optional)", "format", info.commands.get("format", ""))
    opt("Build command (optional)", "build", info.commands.get("build", ""))
    opt(
        "Single test hint (optional)",
        "single_test",
        info.commands.get("single_test", ""),
    )
    info.source_dirs = parse_csv(
        typer.prompt(
            "Source dirs (comma-separated)",
            default=",".join(info.source_dirs) if info.source_dirs else "src",
        )
    )
    info.config_locations = parse_csv(
        typer.prompt(
            "Config locations (comma-separated)",
            default=",".join(info.config_locations) if info.config_locations else "",
        )
    )
    info.branching_model = typer.prompt(
        "Branching model (e.g. main, main+dev, none)",
        default=info.branching_model or "main",
    ).strip()
    info.warnings = parse_csv(
        typer.prompt("Special warnings (comma-separated, optional)", default="").strip()
    )
    return info.normalized()


def print_json(payload: dict[str, object]) -> None:
    import sys

    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
