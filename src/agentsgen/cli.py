from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

import json

from .actions import apply_config, check_repo, load_tool_config, save_tool_config, update_from_config
from .config import ToolConfig
from .detect import detect_repo
from .model import ProjectInfo
from .stacks import adapter_for
from .stacks.base import project_name_from_dir

from . import __version__


app = typer.Typer(
    add_completion=False,
    help="Generate and safely update AGENTS.md/RUNBOOK.md",
    invoke_without_command=True,
    no_args_is_help=True,
)


@app.callback()
def _root(
    version: bool = typer.Option(False, "--version", help="Print version and exit", is_eager=True),
) -> None:
    if version:
        console.print(__version__)
        raise typer.Exit(code=0)
console = Console(stderr=False)
err_console = Console(stderr=True)


def _parse_csv(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x and x.strip()]


def _print_results(results, print_diff: bool) -> None:
    table = Table(title="agentsgen")
    table.add_column("Action", style="bold")
    table.add_column("Path")
    table.add_column("Message")
    for r in results:
        table.add_row(r.action, str(r.path), r.message)
    console.print(table)

    if print_diff:
        for r in results:
            if r.diff:
                console.print(r.diff)


def _interactive_init(
    target: Path,
    defaults: bool,
    stack_opt: str | None,
    name_opt: str | None,
) -> ProjectInfo:
    det = detect_repo(target)
    suggested = str(det.project.get("primary_stack", "static"))
    confidence = "high" if (det.evidence.python or det.evidence.node or det.evidence.make) else "low"
    if suggested == "mixed":
        suggested = "static"

    # In --defaults mode, avoid prompting (safe for non-interactive usage).
    if defaults:
        stack = (stack_opt or suggested).strip().lower()
        project_name = (name_opt or project_name_from_dir(target)).strip()
    else:
        stack = typer.prompt(
            f"Stack (node|python|static) [detected: {suggested}, {confidence}]",
            default=(stack_opt or suggested),
        ).strip().lower()

        project_name = typer.prompt(
            "Project name",
            default=(name_opt or project_name_from_dir(target)),
        ).strip()

    adapter = adapter_for(stack)
    info = adapter.default_info(target, project_name)

    if defaults:
        return info

    # Commands: require install/dev/test (except static can be empty-ish).
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
        pm = typer.prompt("Package manager (npm|pnpm|yarn)", default=info.package_manager or "npm").strip()
        info.package_manager = pm

    if stack == "python":
        tooling = typer.prompt("Python tooling (venv|poetry)", default=info.python_tooling or "venv").strip()
        info.python_tooling = tooling

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

    srcs = typer.prompt(
        "Source dirs (comma-separated)",
        default=",".join(info.source_dirs) if info.source_dirs else "src",
    )
    info.source_dirs = _parse_csv(srcs)

    cfgs = typer.prompt(
        "Config locations (comma-separated)",
        default=",".join(info.config_locations) if info.config_locations else "",
    )
    info.config_locations = _parse_csv(cfgs)

    info.branching_model = typer.prompt(
        "Branching model (e.g. main, main+dev, none)",
        default=info.branching_model or "main",
    ).strip()

    warns = typer.prompt("Special warnings (comma-separated, optional)", default="").strip()
    info.warnings = _parse_csv(warns)

    return info.normalized()


@app.command()
def init(
    target: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    defaults: bool = typer.Option(False, "--defaults", help="Use defaults (no prompts)"),
    stack: str | None = typer.Option(None, "--stack", help="Override stack in --defaults mode"),
    name: str | None = typer.Option(None, "--name", help="Override project name in --defaults mode"),
    autodetect: bool = typer.Option(True, "--autodetect/--no-autodetect", help="Fill config using heuristic detection (read-only)"),
    print_detect: bool = typer.Option(False, "--print-detect", help="Print detection evidence"),
    force_config: bool = typer.Option(False, "--force-config", help="Overwrite .agentsgen.json"),
    prompts: bool = typer.Option(True, "--prompts/--no-prompts", help="Write prompt/execspec.md"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
    print_diff: bool = typer.Option(False, "--print-diff", help="Print unified diff"),
):
    """Initialize a repo: write .agentsgen.json and create/update AGENTS.md + RUNBOOK.md safely."""
    cfg_path = target / ".agentsgen.json"
    cfg: ToolConfig

    if cfg_path.exists() and not force_config:
        cfg = load_tool_config(target)
    else:
        if autodetect:
            det = detect_repo(target)
            if print_detect:
                err_console.print(json.dumps(det.to_json(), indent=2))
            cfg = ToolConfig.from_detect(det)
            if name:
                cfg.project["name"] = name
            if stack:
                cfg.project["primary_stack"] = stack
            cfg = ToolConfig.from_json(cfg.to_json())
        else:
            info = _interactive_init(target, defaults=defaults, stack_opt=stack, name_opt=name)
            cfg = ToolConfig.from_project_info(info)

        if not dry_run:
            save_tool_config(target, cfg)

    results = apply_config(target, cfg, write_prompts=prompts, dry_run=dry_run, print_diff=print_diff)

    # Any error result => exit 1.
    errors = [r for r in results if r.action == "error"]
    _print_results(results, print_diff=print_diff)

    if errors:
        for e in errors:
            err_console.print(f"ERROR: {e.path}: {e.message}")
        raise typer.Exit(code=1)


@app.command()
def update(
    target: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
    print_diff: bool = typer.Option(False, "--print-diff", help="Print unified diff"),
):
    """Update only marked sections in AGENTS.md/RUNBOOK.md using .agentsgen.json."""
    try:
        results = update_from_config(target, dry_run=dry_run, print_diff=print_diff)
    except FileNotFoundError:
        err_console.print("ERROR: Missing .agentsgen.json. Run: agentsgen init")
        raise typer.Exit(code=1)

    errors = [r for r in results if r.action == "error"]
    _print_results(results, print_diff=print_diff)

    if errors:
        for e in errors:
            err_console.print(f"ERROR: {e.path}: {e.message}")
        raise typer.Exit(code=1)


@app.command(name="check")
def check_cmd(
    target: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
):
    """Validate that repo is agentsgen-ready. Non-zero exit code on problems."""
    code, problems, warnings = check_repo(target)
    for w in warnings:
        err_console.print(f"WARN: {w}")
    if problems:
        for p in problems:
            err_console.print(f"- {p}")
    raise typer.Exit(code=code)


@app.command()
def doctor(
    target: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
):
    """Alias for check."""
    code, problems, warnings = check_repo(target)
    for w in warnings:
        err_console.print(f"WARN: {w}")
    if problems:
        for p in problems:
            err_console.print(f"- {p}")
    raise typer.Exit(code=code)

@app.command()
def detect(
    repo: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    format: str = typer.Option("text", "--format", help="Output format: text|json"),
    explain: bool = typer.Option(False, "--explain", help="Print rationale (why detection chose these values)"),
):
    """Detect stack/tooling/commands using safe heuristics and print evidence."""
    det = detect_repo(repo)
    if format == "json":
        console.print(json.dumps(det.to_json(), indent=2))
        raise typer.Exit(code=0)

    console.print(f"primary_stack: {det.project.get('primary_stack')}")
    if det.commands:
        console.print("commands:")
        for k in sorted(det.commands.keys()):
            console.print(f"- {k}: {det.commands[k]}")
    else:
        console.print("commands: (none)")

    if explain and det.rationale:
        console.print("rationale:")
        for r in det.rationale:
            console.print(f"- {r}")

    console.print("evidence:")
    for k, v in det.to_json().get("evidence", {}).items():
        if v:
            console.print(f"- {k}: {', '.join(v)}")


def main(argv: list[str] | None = None) -> None:
    app(prog_name="agentsgen")


if __name__ == "__main__":
    main(sys.argv[1:])
