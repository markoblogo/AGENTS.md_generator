from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

import json

from .actions import (
    aggregate_check,
    apply_pack,
    apply_config,
    generate_readme_snippets,
    load_tool_config,
    pack_plan_specs,
    save_tool_config,
    status_repo,
    update_from_config,
)
from .config import ToolConfig, merge_detect_hints
from .presets import list_presets, load_preset_config
from .detect import detect_repo
from .model import ProjectInfo
from .stacks import adapter_for
from .stacks.base import project_name_from_dir
from .analyze import apply_analysis
from .meta import apply_metadata
from .understand import apply_understanding

from . import __version__
from .constants import (
    AGENTS_FILENAME,
    AGENTS_GENERATED_FILENAME,
    CONFIG_FILENAME,
    RUNBOOK_FILENAME,
    RUNBOOK_GENERATED_FILENAME,
)


app = typer.Typer(
    add_completion=False,
    help="Generate and safely update AGENTS.md/RUNBOOK.md",
    invoke_without_command=True,
    no_args_is_help=True,
)


@app.callback()
def _root(
    version: bool = typer.Option(
        False, "--version", help="Print version and exit", is_eager=True
    ),
) -> None:
    if version:
        console.print(__version__)
        raise typer.Exit(code=0)


console = Console(stderr=False)
err_console = Console(stderr=True)


def _parse_csv(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x and x.strip()]


def _resolve_repo_file(target: Path, supplied: Path | None, default_name: str) -> Path:
    if supplied is None:
        return target / default_name
    return supplied if supplied.is_absolute() else target / supplied


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


def _results_payload(results) -> list[dict[str, object]]:
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


def _path_relative_to_target(path: Path, target: Path) -> str:
    try:
        return str(path.resolve().relative_to(target.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _pack_plan_payload(
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
    for r in results:
        if r.action not in ("created", "updated", "generated"):
            continue
        rel = _path_relative_to_target(r.path, target)
        action = {"created": "create", "updated": "update", "generated": "generate"}[
            r.action
        ]
        rows.append(
            {
                "path": rel,
                "action": action,
                "sections": list(sections_map.get(rel, [])),
                "message": r.message,
            }
        )
    return sorted(rows, key=lambda x: str(x["path"]))


def _print_pack_plan(plan: list[dict[str, object]]) -> None:
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


def _print_pack_plan_header(
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


def _interactive_init(
    target: Path,
    defaults: bool,
    stack_opt: str | None,
    name_opt: str | None,
) -> ProjectInfo:
    det = detect_repo(target)
    suggested = str(det.project.get("primary_stack", "static"))
    confidence = (
        "high"
        if (det.evidence.python or det.evidence.node or det.evidence.make)
        else "low"
    )
    if suggested == "mixed":
        suggested = "static"

    # In --defaults mode, avoid prompting (safe for non-interactive usage).
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
        pm = typer.prompt(
            "Package manager (npm|pnpm|yarn)", default=info.package_manager or "npm"
        ).strip()
        info.package_manager = pm

    if stack == "python":
        tooling = typer.prompt(
            "Python tooling (venv|poetry)", default=info.python_tooling or "venv"
        ).strip()
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

    warns = typer.prompt(
        "Special warnings (comma-separated, optional)", default=""
    ).strip()
    info.warnings = _parse_csv(warns)

    return info.normalized()


@app.command()
def presets() -> None:
    """List available init presets."""
    rows = list_presets()
    if not rows:
        console.print("No presets available.")
        raise typer.Exit(code=1)

    for row in rows:
        console.print(f"- {row.name}: {row.description}")
        console.print(f"  example: {row.example}")


@app.command()
def init(
    target: Path = typer.Argument(
        Path("."), exists=True, file_okay=False, dir_okay=True
    ),
    defaults: bool = typer.Option(
        False, "--defaults", help="Use defaults (no prompts)"
    ),
    stack: str | None = typer.Option(
        None, "--stack", help="Override stack in --defaults mode"
    ),
    name: str | None = typer.Option(
        None, "--name", help="Override project name in --defaults mode"
    ),
    preset: str | None = typer.Option(
        None, "--preset", help="Start from a built-in preset config"
    ),
    autodetect: bool = typer.Option(
        True,
        "--autodetect/--no-autodetect",
        help="Fill config using heuristic detection (read-only)",
    ),
    print_detect: bool = typer.Option(
        False, "--print-detect", help="Print detection evidence"
    ),
    force_config: bool = typer.Option(
        False, "--force-config", help="Overwrite .agentsgen.json"
    ),
    prompts: bool = typer.Option(
        True, "--prompts/--no-prompts", help="Write prompt/execspec.md"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
    print_diff: bool = typer.Option(False, "--print-diff", help="Print unified diff"),
):
    """Initialize a repo: write .agentsgen.json and create/update AGENTS.md + RUNBOOK.md safely."""
    cfg_path = target / ".agentsgen.json"
    cfg: ToolConfig
    preset_cfg: ToolConfig | None = None

    if preset:
        try:
            preset_cfg = load_preset_config(preset)
        except KeyError:
            console.print(f"ERROR: Unknown preset '{preset}'. Run: agentsgen presets")
            raise typer.Exit(code=1)

    if cfg_path.exists() and not force_config:
        cfg = load_tool_config(target)
        if preset:
            console.print(
                f"Using existing {CONFIG_FILENAME}; preset '{preset}' not applied. Use --force-config to replace it."
            )
        if autodetect:
            det = detect_repo(target)
            det_cfg = ToolConfig.from_detect(det)
            cfg = merge_detect_hints(cfg, det_cfg)
            if not dry_run:
                save_tool_config(target, cfg)
    else:
        if preset:
            cfg = preset_cfg
            if autodetect:
                det = detect_repo(target)
                if print_detect:
                    err_console.print(json.dumps(det.to_json(), indent=2))
                cfg = merge_detect_hints(cfg, ToolConfig.from_detect(det))
            if name:
                cfg.project["name"] = name
            if stack:
                cfg.project["primary_stack"] = stack
            cfg = ToolConfig.from_json(cfg.to_json())
        elif autodetect:
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
            info = _interactive_init(
                target, defaults=defaults, stack_opt=stack, name_opt=name
            )
            cfg = ToolConfig.from_project_info(info)

        if not dry_run:
            save_tool_config(target, cfg)

    results = apply_config(
        target, cfg, write_prompts=prompts, dry_run=dry_run, print_diff=print_diff
    )

    # Any error result => exit 1.
    errors = [r for r in results if r.action == "error"]
    _print_results(results, print_diff=print_diff)

    if errors:
        for e in errors:
            err_console.print(f"ERROR: {e.path}: {e.message}")
        raise typer.Exit(code=1)


@app.command()
def update(
    target: Path = typer.Argument(
        Path("."), exists=True, file_okay=False, dir_okay=True
    ),
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


@app.command()
def pack(
    target: Path = typer.Argument(
        Path("."), exists=True, file_okay=False, dir_okay=True
    ),
    autodetect: bool = typer.Option(
        True,
        "--autodetect/--no-autodetect",
        help="Use read-only stack/command detection before rendering pack",
    ),
    stack: str | None = typer.Option(
        None, "--stack", help="Override stack for pack templates (python|node|static)"
    ),
    llms_format: str | None = typer.Option(
        None, "--llms-format", help="Manifest format: txt|md"
    ),
    output_dir: str | None = typer.Option(
        None, "--output-dir", help="Where to write docs (default docs/ai)"
    ),
    files: str | None = typer.Option(
        None,
        "--files",
        help="Comma-separated allowlist (e.g. llms,how-to-run.md,SECURITY_AI.md)",
    ),
    site: str | None = typer.Option(
        None,
        "--site",
        help="Generate llms.txt from a public site URL instead of repo heuristics",
    ),
    check: bool = typer.Option(
        False,
        "--check",
        help="Validate that pack files are up to date (non-zero if drift is detected)",
    ),
    format: str = typer.Option(
        "text",
        "--format",
        help="Output format: text|json",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
    print_diff: bool = typer.Option(False, "--print-diff", help="Print unified diff"),
    print_plan: bool = typer.Option(
        False, "--print-plan", help="Print dry pack plan (no file writes)"
    ),
):
    """Generate/update LLMO pack files with marker-safe updates."""
    cfg_path = target / ".agentsgen.json"
    cfg = load_tool_config(target) if cfg_path.exists() else ToolConfig()

    if autodetect:
        det_cfg = ToolConfig.from_detect(detect_repo(target))
        existing_pack = cfg.pack
        cfg = merge_detect_hints(cfg, det_cfg)
        cfg.pack = existing_pack
    elif not cfg_path.exists():
        info = _interactive_init(target, defaults=True, stack_opt=stack, name_opt=None)
        cfg = ToolConfig.from_project_info(info)

    if stack:
        cfg.project["primary_stack"] = stack.strip().lower()
        cfg = ToolConfig.from_json(cfg.to_json())

    if llms_format:
        cfg.pack.llms_format = llms_format.strip().lower()
    if output_dir:
        cfg.pack.output_dir = output_dir.strip()
    if files is not None:
        cfg.pack.files = _parse_csv(files)

    dry_run_effective = dry_run or check or print_plan
    results = apply_pack(
        target,
        cfg,
        autodetect=autodetect,
        site_url=site,
        dry_run=dry_run_effective,
        print_diff=(print_diff and not print_plan),
    )
    errors = [r for r in results if r.action == "error"]
    drift = any(
        r.action in ("created", "updated", "generated") and r.changed for r in results
    )

    status = "ok"
    if errors:
        status = "error"
    elif check and drift:
        status = "drift"

    summary = (
        f"pack:{status} "
        f"(created={sum(1 for r in results if r.action == 'created')}, "
        f"updated={sum(1 for r in results if r.action == 'updated')}, "
        f"generated={sum(1 for r in results if r.action == 'generated')}, "
        f"errors={len(errors)})"
    )

    if print_plan:
        plan = _pack_plan_payload(
            target=target,
            cfg=cfg,
            autodetect=autodetect,
            results=results,
        )
        if format == "json":
            sys.stdout.write(
                json.dumps(
                    {
                        "version": 1,
                        "status": status,
                        "summary": summary,
                        "check": check,
                        "dry_run": True,
                        "print_plan": True,
                        "plan": plan,
                    },
                    indent=2,
                )
                + "\n"
            )
        else:
            _print_pack_plan_header(
                target=target,
                autodetect=autodetect,
                output_dir=cfg.pack.output_dir,
                files_count=len(plan),
            )
            _print_pack_plan(plan)
            console.print(summary)
            if check and drift:
                err_console.print(
                    "Pack drift detected. Run `agentsgen pack` to update generated files."
                )

        if check and (errors or drift):
            raise typer.Exit(code=1)
        # print-plan alone is always a dry preview with exit 0.
        raise typer.Exit(code=0)

    if format == "json":
        sys.stdout.write(
            json.dumps(
                {
                    "status": status,
                    "summary": summary,
                    "check": check,
                    "dry_run": dry_run_effective,
                    "results": _results_payload(results),
                },
                indent=2,
            )
            + "\n"
        )
    else:
        _print_results(results, print_diff=print_diff)
        console.print(summary)
        if check and drift:
            err_console.print(
                "Pack drift detected. Run `agentsgen pack` to update generated files."
            )

    if errors:
        for e in errors:
            err_console.print(f"ERROR: {e.path}: {e.message}")
        raise typer.Exit(code=1)
    if check and drift:
        raise typer.Exit(code=1)


@app.command(name="check")
def check_cmd(
    target: Path = typer.Argument(
        Path("."), exists=True, file_okay=False, dir_okay=True
    ),
    format: str = typer.Option("text", "--format", help="Output format: text|json"),
    ci: bool = typer.Option(
        False, "--ci", help="Print compact CI-friendly text output"
    ),
    pack_check: bool = typer.Option(
        False, "--pack-check", help="Run pack --check as part of check"
    ),
    snippets_check: bool = typer.Option(
        False, "--snippets-check", help="Run snippets --check as part of check"
    ),
    run_all: bool = typer.Option(
        False, "--all", help="Enable both --pack-check and --snippets-check"
    ),
):
    """Validate that repo is agentsgen-ready. Non-zero exit code on problems."""
    effective_pack_check = pack_check or run_all
    effective_snippets_check = snippets_check or run_all
    report = aggregate_check(
        target,
        pack_check=effective_pack_check,
        snippets_check=effective_snippets_check,
    )

    if format == "json":
        sys.stdout.write(json.dumps(report.to_json(), indent=2) + "\n")
    else:
        core = report.checks["core"]
        pack = report.checks["pack"]
        snippets = report.checks["snippets"]

        if ci:
            # CI mode avoids absolute paths to keep logs compact and wrapping-stable.
            status_line = report.status.upper()
            print(f"agentsgen check: {status_line}")

            def _ci_line(label: str, block: dict[str, object] | None) -> None:
                if block is None:
                    print(f"{label}: skipped")
                    return
                block_status = str(block.get("status", "ok"))
                count = int(block.get("drift_count", 0)) + int(
                    block.get("error_count", 0)
                )
                suffix = f" ({count})" if count else ""
                print(f"{label}: {block_status}{suffix}")

            _ci_line("core", core)
            _ci_line("pack", pack if isinstance(pack, dict) else None)
            _ci_line("snippets", snippets if isinstance(snippets, dict) else None)

            if report.status == "drift":
                print("remediation:")
                if str(core.get("status")) == "drift":
                    print("  agentsgen update .")
                if isinstance(pack, dict) and str(pack.get("status")) == "drift":
                    print("  agentsgen pack . --autodetect")
                if (
                    isinstance(snippets, dict)
                    and str(snippets.get("status")) == "drift"
                ):
                    print("  agentsgen snippets .")
        else:
            for item in core.get("results", []):
                if item["level"] == "warning":
                    err_console.print(f"WARN: {item['message']}")
                else:
                    err_console.print(f"- {item['message']}")

            if isinstance(pack, dict):
                console.print(f"Pack check: {pack['status']}")
            if isinstance(snippets, dict):
                if snippets.get("status") == "skipped":
                    console.print(
                        f"Snippets check: skipped ({snippets.get('reason', 'n/a')})"
                    )
                else:
                    console.print(f"Snippets check: {snippets['status']}")
            console.print(f"Summary: {report.status.upper()}")

    exit_code = 0 if report.status == "ok" else (2 if report.status == "error" else 1)
    raise typer.Exit(code=exit_code)


@app.command()
def doctor(
    target: Path = typer.Argument(
        Path("."), exists=True, file_okay=False, dir_okay=True
    ),
    format: str = typer.Option("text", "--format", help="Output format: text|json"),
    ci: bool = typer.Option(
        False, "--ci", help="Print compact CI-friendly text output"
    ),
    pack_check: bool = typer.Option(
        False, "--pack-check", help="Run pack --check as part of check"
    ),
    snippets_check: bool = typer.Option(
        False, "--snippets-check", help="Run snippets --check as part of check"
    ),
    run_all: bool = typer.Option(
        False, "--all", help="Enable both --pack-check and --snippets-check"
    ),
):
    """Alias for check."""
    ctx = typer.get_current_context()
    ctx.invoke(
        check_cmd,
        target=target,
        format=format,
        ci=ci,
        pack_check=pack_check,
        snippets_check=snippets_check,
        run_all=run_all,
    )


@app.command()
def status(
    target: Path = typer.Argument(
        Path("."), exists=True, file_okay=False, dir_okay=True
    ),
    format: str = typer.Option("text", "--format", help="Output format: text|json"),
    quiet: bool = typer.Option(
        False, "--quiet", help="Print only summary line in text mode"
    ),
):
    """Read-only repo status overview for managed files, markers, pack, and drift."""
    report = status_repo(target)
    payload = report.to_json()
    code = 0 if report.status == "ok" else (2 if report.status == "error" else 1)

    if format == "json":
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        raise typer.Exit(code=code)

    summary = f"Summary: {report.status.upper()}"
    if quiet:
        console.print(summary)
        raise typer.Exit(code=code)

    console.print(f"Repo: {report.path}")
    console.print(f"Config: {'present' if report.config.get('present') else 'missing'}")
    console.print(
        f"AGENTS.md: {'present' if report.agents_md.present else 'missing'}, markers: {'yes' if report.agents_md.markers else 'no'}, sections: {report.agents_md.marker_sections}, generated sibling: {'yes' if report.agents_md.generated_sibling else 'no'}"
    )
    console.print(
        f"RUNBOOK.md: {'present' if report.runbook_md.present else 'missing'}, markers: {'yes' if report.runbook_md.markers else 'no'}, sections: {report.runbook_md.marker_sections}, generated sibling: {'yes' if report.runbook_md.generated_sibling else 'no'}"
    )
    console.print(
        f"Pack: {report.pack['status']} ({len(report.pack['findings'])} findings)"
    )
    if report.generated["files"]:
        console.print(f"Generated siblings: {', '.join(report.generated['files'])}")
    for finding in report.pack["findings"]:
        console.print(f"- {finding}")
    if not quiet:
        # Reconstruct high-level file findings from structured payload.
        if not report.config.get("present"):
            console.print(f"- Missing {CONFIG_FILENAME}")
        if not report.agents_md.present:
            console.print(f"- Missing {AGENTS_FILENAME}")
        elif not report.agents_md.markers:
            console.print(
                f"- {AGENTS_FILENAME} has no AGENTSGEN markers (updates will go to generated siblings)"
            )
        if report.agents_md.generated_sibling:
            console.print(
                f"- Generated sibling exists for {AGENTS_FILENAME}: {AGENTS_GENERATED_FILENAME}"
            )
        if not report.runbook_md.present:
            console.print(f"- Missing {RUNBOOK_FILENAME}")
        elif not report.runbook_md.markers:
            console.print(
                f"- {RUNBOOK_FILENAME} has no AGENTSGEN markers (updates will go to generated siblings)"
            )
        if report.runbook_md.generated_sibling:
            console.print(
                f"- Generated sibling exists for {RUNBOOK_FILENAME}: {RUNBOOK_GENERATED_FILENAME}"
            )
    if report.summary["errors"]:
        console.print(f"Errors: {report.summary['errors']}")
    console.print(summary)
    raise typer.Exit(code=code)


@app.command()
def snippets(
    target: Path = typer.Argument(
        Path("."), exists=True, file_okay=False, dir_okay=True
    ),
    readme: Path | None = typer.Option(
        None, "--readme", help="README source file (default README.md)"
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Generated output file (default README_SNIPPETS.generated.md)",
    ),
    check: bool = typer.Option(
        False, "--check", help="Validate generated snippets output without writing"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
    print_diff: bool = typer.Option(False, "--print-diff", help="Print unified diff"),
    format: str = typer.Option("text", "--format", help="Output format: text|json"),
):
    """Generate or validate README snippet extracts from AGENTSGEN snippet markers."""
    readme_path = _resolve_repo_file(target, readme, "README.md")
    output_path = _resolve_repo_file(target, output, "README_SNIPPETS.generated.md")

    report = generate_readme_snippets(
        target,
        readme_path=readme_path,
        output_path=output_path,
        check=check,
        dry_run=dry_run or check,
        print_diff=print_diff,
    )

    code = 0 if report.status == "ok" else (2 if report.status == "error" else 1)

    if format == "json":
        sys.stdout.write(json.dumps(report.to_json(), indent=2) + "\n")
        raise typer.Exit(code=code)

    if report.message == "no snippets found":
        console.print("no snippets found")
        if report.diff:
            console.print(report.diff)
        raise typer.Exit(code=code)

    if report.status == "error":
        err_console.print(f"ERROR: {report.message}")
        raise typer.Exit(code=code)

    console.print(f"README: {report.readme_path}")
    console.print(f"Output: {report.output_path}")
    console.print(f"Snippets: {report.snippets_count}")
    for snippet in report.snippets:
        console.print(
            f"- {snippet.name} (lines {snippet.start_line}-{snippet.end_line})"
        )
    if report.diff:
        console.print(report.diff)

    summary = "Summary: OK" if report.status == "ok" else "Summary: DRIFT"
    console.print(summary)
    raise typer.Exit(code=code)


@app.command()
def understand(
    target: Path = typer.Argument(
        Path("."), exists=True, file_okay=False, dir_okay=True
    ),
    format: str = typer.Option("text", "--format", help="Output format: text|json"),
    output_dir: str = typer.Option(
        "docs/ai", "--output-dir", help="Where to write repomap.md and graph.mmd"
    ),
    compact_budget: int = typer.Option(
        4000,
        "--compact-budget",
        min=256,
        help="Approximate token budget for repomap.compact.md",
    ),
):
    """Generate deterministic repo understanding artifacts."""
    out_dir = Path(output_dir)
    if not out_dir.is_absolute():
        out_dir = target / out_dir

    results, payload = apply_understanding(
        target,
        output_dir=out_dir,
        compact_budget_tokens=compact_budget,
    )
    errors = [row for row in results if row.action == "error"]
    response = {
        "version": 1,
        "command": "understand",
        "path": str(target),
        "output_dir": str(out_dir),
        "stack": payload["stack"],
        "summary": payload["summary"],
        "changed_files": payload["knowledge"].get("changed_files", []),
        "relevance": payload["knowledge"].get("relevance", []),
        "results": _results_payload(results),
    }

    if format == "json":
        sys.stdout.write(json.dumps(response, indent=2) + "\n")
    else:
        _print_results(results, print_diff=False)
        console.print(f"stack: {payload['stack']}")
        console.print(
            "summary: "
            f"files={payload['summary']['files_count']} "
            f"edges={payload['summary']['edges_count']} "
            f"entrypoints={payload['summary']['entrypoints_count']} "
            f"changed={payload['summary']['changed_files_count']} "
            f"compact_budget={payload['summary']['compact_budget_tokens']}"
        )

    if errors:
        raise typer.Exit(code=1)


@app.command()
def analyze(
    url: str = typer.Argument(..., help="Website URL to analyze"),
    target: Path = typer.Argument(
        Path("."), exists=True, file_okay=False, dir_okay=True
    ),
    format: str = typer.Option("text", "--format", help="Output format: text|json"),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Output JSON file (default docs/ai/llmo-score.json)",
    ),
    use_ai: bool = typer.Option(
        False,
        "--use-ai",
        help="Add an advisory OpenAI review (requires OPENAI_API_KEY)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
):
    """Analyze a public website for AI discoverability using deterministic heuristics."""
    output_path = _resolve_repo_file(target, output, "docs/ai/llmo-score.json")

    try:
        results, payload = apply_analysis(
            target,
            url=url,
            output_path=output_path,
            use_ai=use_ai,
            dry_run=dry_run,
        )
    except ValueError as exc:
        err_console.print(f"ERROR: {exc}")
        raise typer.Exit(code=1)

    errors = [row for row in results if row.action == "error"]
    response = {
        "version": 1,
        "command": "analyze",
        "path": str(target),
        "output": str(output_path),
        "result": payload,
        "results": _results_payload(results),
    }

    if format == "json":
        sys.stdout.write(json.dumps(response, indent=2) + "\n")
    else:
        _print_results(results, print_diff=False)
        console.print(f"url: {payload['url']}")
        console.print(f"score: {payload['score']}/100 ({payload['visibility']})")
        console.print(f"summary: {payload['summary']}")
        if payload["recommendations"]:
            console.print("recommendations:")
            for item in payload["recommendations"][:5]:
                console.print(f"- {item}")
        if use_ai and payload.get("ai_review"):
            console.print("ai_review: included")

    if errors:
        raise typer.Exit(code=1)


@app.command()
def meta(
    url: str = typer.Argument(..., help="Website URL to generate metadata for"),
    target: Path = typer.Argument(
        Path("."), exists=True, file_okay=False, dir_okay=True
    ),
    format: str = typer.Option("text", "--format", help="Output format: text|json"),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Output JSON file (default docs/ai/llmo-meta.json)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
):
    """Generate AI-oriented metadata suggestions for a public website."""
    output_path = _resolve_repo_file(target, output, "docs/ai/llmo-meta.json")

    try:
        results, payload = apply_metadata(
            target,
            url=url,
            output_path=output_path,
            dry_run=dry_run,
        )
    except ValueError as exc:
        err_console.print(f"ERROR: {exc}")
        raise typer.Exit(code=1)

    errors = [row for row in results if row.action == "error"]
    response = {
        "version": 1,
        "command": "meta",
        "path": str(target),
        "output": str(output_path),
        "result": payload,
        "results": _results_payload(results),
    }

    if format == "json":
        sys.stdout.write(json.dumps(response, indent=2) + "\n")
    else:
        _print_results(results, print_diff=False)
        console.print(f"url: {payload['url']}")
        console.print(f"title: {payload['result']['title']}")
        console.print(f"description: {payload['result']['description']}")
        if payload["result"]["keywords"]:
            console.print("keywords: " + ", ".join(payload["result"]["keywords"]))

    if errors:
        raise typer.Exit(code=1)


@app.command()
def detect(
    repo: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    format: str = typer.Option("text", "--format", help="Output format: text|json"),
    explain: bool = typer.Option(
        False, "--explain", help="Print rationale (why detection chose these values)"
    ),
):
    """Detect stack/tooling/commands using safe heuristics and print evidence."""
    det = detect_repo(repo)
    if format == "json":
        sys.stdout.write(json.dumps(det.to_json(), indent=2) + "\n")
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
