from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from . import __version__
from .actions import (
    aggregate_check,
    apply_pack,
    generate_readme_snippets,
    load_tool_config,
    save_tool_config,
    status_repo,
)
from .cli_support import (
    console,
    err_console,
    interactive_init as _interactive_init,
    print_results as _print_results,
    results_payload as _results_payload,
)
from .config import ToolConfig, merge_detect_hints
from .constants import (
    AGENTS_FILENAME,
    AGENTS_GENERATED_FILENAME,
    CONFIG_FILENAME,
    RUNBOOK_FILENAME,
    RUNBOOK_GENERATED_FILENAME,
)
from .detect import detect_repo
from .patch_engine import apply_config, update_from_config
from .presets import list_presets, load_preset_config


def _enabled_check_blocks(report) -> list[tuple[str, dict[str, object]]]:
    blocks: list[tuple[str, dict[str, object]]] = []
    for name, block in report.checks.items():
        if isinstance(block, dict):
            blocks.append((str(name), block))
    return blocks


def _readiness_score(report) -> tuple[int, str]:
    drift = sum(
        1
        for _name, block in _enabled_check_blocks(report)
        if str(block.get("status")) == "drift"
    )
    errors = sum(
        1
        for _name, block in _enabled_check_blocks(report)
        if str(block.get("status")) == "error"
    )
    warnings = sum(
        int(block.get("warnings_count", 0))
        for _name, block in _enabled_check_blocks(report)
    )
    score = max(0, 100 - errors * 35 - drift * 20 - warnings * 5)
    if errors:
        level = "blocked"
    elif score >= 90:
        level = "ready"
    elif score >= 70:
        level = "reviewable"
    else:
        level = "needs work"
    return score, level


def _remediation_commands(report) -> list[str]:
    commands: list[str] = []
    core = report.checks.get("core")
    pack = report.checks.get("pack")
    snippets = report.checks.get("snippets")
    if isinstance(core, dict) and str(core.get("status")) == "drift":
        commands.append("agentsgen fix .")
    if isinstance(pack, dict) and str(pack.get("status")) == "drift":
        commands.append("agentsgen fix . --pack")
    if isinstance(snippets, dict) and str(snippets.get("status")) == "drift":
        commands.append("agentsgen fix . --snippets")
    if len(commands) > 1:
        commands.append("agentsgen fix . --all")
    return commands


def _print_readiness_report(report) -> None:
    score, level = _readiness_score(report)
    console.print(f"Agent Readiness Score: {score}/100")
    console.print(f"Readiness level: {level}")
    console.print(f"Overall status: {report.status}")
    for name, block in _enabled_check_blocks(report):
        status = str(block.get("status", "ok"))
        drift = int(block.get("drift_count", 0))
        errors = int(block.get("error_count", 0))
        warnings = int(block.get("warnings_count", 0))
        suffix = []
        if drift:
            suffix.append(f"drift={drift}")
        if errors:
            suffix.append(f"errors={errors}")
        if warnings:
            suffix.append(f"warnings={warnings}")
        detail = f" ({', '.join(suffix)})" if suffix else ""
        console.print(f"- {name}: {status}{detail}")

    commands = _remediation_commands(report)
    if commands:
        console.print("Recommended fixes:")
        for command in commands:
            console.print(f"  {command}")


def register_core_commands(app: typer.Typer) -> None:
    @app.callback()
    def _root(
        version: bool = typer.Option(
            False, "--version", help="Print version and exit", is_eager=True
        ),
    ) -> None:
        if version:
            console.print(__version__)
            raise typer.Exit(code=0)

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
        interactive: bool = typer.Option(
            False,
            "--interactive",
            help="Force the interactive wizard instead of pure autodetect defaults",
        ),
        llm_enhance: bool = typer.Option(
            False,
            "--llm-enhance",
            help="Opt-in narrative enhancement grounded in local understand artifacts",
        ),
        llm_provider: str = typer.Option(
            "",
            "--llm-provider",
            help="LLM provider for --llm-enhance (openai|anthropic)",
        ),
        dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
        print_diff: bool = typer.Option(
            False, "--print-diff", help="Print unified diff"
        ),
    ):
        """Initialize a repo: write .agentsgen.json and create/update AGENTS.md + RUNBOOK.md safely."""
        cfg_path = target / ".agentsgen.json"
        cfg: ToolConfig
        preset_cfg: ToolConfig | None = None

        if preset:
            try:
                preset_cfg = load_preset_config(preset)
            except KeyError:
                console.print(
                    f"ERROR: Unknown preset '{preset}'. Run: agentsgen presets"
                )
                raise typer.Exit(code=1)

        if cfg_path.exists() and not force_config:
            try:
                cfg = load_tool_config(target)
            except Exception as exc:
                err_console.print(f"ERROR: Invalid {CONFIG_FILENAME}: {exc}")
                raise typer.Exit(code=1)
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
            elif autodetect and not interactive:
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
            target,
            cfg,
            write_prompts=prompts,
            dry_run=dry_run,
            print_diff=print_diff,
            llm_provider=llm_provider if llm_enhance else "",
        )

        errors = [r for r in results if r.action == "error"]
        _print_results(results, print_diff=print_diff)

        if errors:
            for error in errors:
                err_console.print(f"ERROR: {error.path}: {error.message}")
            raise typer.Exit(code=1)

    @app.command()
    def update(
        target: Path = typer.Argument(
            Path("."), exists=True, file_okay=False, dir_okay=True
        ),
        llm_enhance: bool = typer.Option(
            False,
            "--llm-enhance",
            help="Opt-in narrative enhancement grounded in local understand artifacts",
        ),
        llm_provider: str = typer.Option(
            "",
            "--llm-provider",
            help="LLM provider for --llm-enhance (openai|anthropic)",
        ),
        dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
        print_diff: bool = typer.Option(
            False, "--print-diff", help="Print unified diff"
        ),
    ):
        """Update only marked sections in AGENTS.md/RUNBOOK.md using .agentsgen.json."""
        try:
            results = update_from_config(
                target,
                dry_run=dry_run,
                print_diff=print_diff,
                llm_provider=llm_provider if llm_enhance else "",
            )
        except FileNotFoundError:
            err_console.print("ERROR: Missing .agentsgen.json. Run: agentsgen init")
            raise typer.Exit(code=1)
        except Exception as exc:
            err_console.print(f"ERROR: Invalid {CONFIG_FILENAME}: {exc}")
            raise typer.Exit(code=1)

        errors = [r for r in results if r.action == "error"]
        _print_results(results, print_diff=print_diff)

        if errors:
            for error in errors:
                err_console.print(f"ERROR: {error.path}: {error.message}")
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
        report_mode: bool = typer.Option(
            False,
            "--report",
            help="Print agent-readiness score and remediation commands",
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
            payload = report.to_json()
            if report_mode:
                score, level = _readiness_score(report)
                payload["readiness"] = {
                    "score": score,
                    "level": level,
                    "remediation": _remediation_commands(report),
                }
            sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        else:
            core = report.checks["core"]
            pack = report.checks["pack"]
            snippets = report.checks["snippets"]

            if report_mode:
                _print_readiness_report(report)
            elif ci:
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

        exit_code = (
            0 if report.status == "ok" else (2 if report.status == "error" else 1)
        )
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
        report_mode: bool = typer.Option(
            False,
            "--report",
            help="Print agent-readiness score and remediation commands",
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
            report_mode=report_mode,
        )

    @app.command()
    def fix(
        target: Path = typer.Argument(
            Path("."), exists=True, file_okay=False, dir_okay=True
        ),
        pack: bool = typer.Option(
            False, "--pack", help="Also refresh pack artifacts with autodetect"
        ),
        snippets: bool = typer.Option(
            False, "--snippets", help="Also refresh README snippet output"
        ),
        run_all: bool = typer.Option(
            False, "--all", help="Enable both --pack and --snippets"
        ),
        autodetect: bool = typer.Option(
            True,
            "--autodetect/--no-autodetect",
            help="Use read-only detection before rendering pack artifacts",
        ),
        dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
        print_diff: bool = typer.Option(
            False, "--print-diff", help="Print unified diff"
        ),
        format: str = typer.Option("text", "--format", help="Output format: text|json"),
    ):
        """Safely remediate common agentsgen drift using marker-owned updates."""
        try:
            doc_results = update_from_config(
                target, dry_run=dry_run, print_diff=print_diff
            )
        except FileNotFoundError:
            err_console.print("ERROR: Missing .agentsgen.json. Run: agentsgen init")
            raise typer.Exit(code=1)
        except Exception as exc:
            err_console.print(f"ERROR: Invalid {CONFIG_FILENAME}: {exc}")
            raise typer.Exit(code=1)

        effective_pack = pack or run_all
        effective_snippets = snippets or run_all
        pack_results = []
        snippets_payload: dict[str, object] | None = None

        if effective_pack:
            cfg = load_tool_config(target)
            if autodetect:
                det_cfg = ToolConfig.from_detect(detect_repo(target))
                existing_pack = cfg.pack
                cfg = merge_detect_hints(cfg, det_cfg)
                cfg.pack = existing_pack
            pack_results = apply_pack(
                target,
                cfg,
                autodetect=autodetect,
                dry_run=dry_run,
                print_diff=print_diff,
            )

        if effective_snippets:
            snippet_report = generate_readme_snippets(
                target,
                readme_path=target / "README.md",
                output_path=target / "README_SNIPPETS.generated.md",
                check=False,
                dry_run=dry_run,
                print_diff=print_diff,
            )
            snippets_payload = snippet_report.to_json()

        all_results = list(doc_results) + list(pack_results)
        errors = [r for r in all_results if r.action == "error"]
        snippet_errors: list[str] = []
        if snippets_payload and snippets_payload.get("status") == "error":
            snippet_errors.append(
                str(snippets_payload.get("message", "snippets error"))
            )
        changed = sum(1 for r in all_results if bool(r.changed))
        status = "error" if errors or snippet_errors else "ok"
        error_count = len(errors) + len(snippet_errors)
        summary = f"fix:{status} (changed={changed}, errors={error_count})"

        if format == "json":
            payload = {
                "version": 1,
                "command": "fix",
                "status": status,
                "summary": summary,
                "dry_run": dry_run,
                "docs": _results_payload(doc_results),
                "pack": _results_payload(pack_results),
                "snippets": snippets_payload,
            }
            sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        else:
            _print_results(all_results, print_diff=print_diff)
            if snippets_payload is not None:
                output_path = snippets_payload.get("output_path")
                console.print(
                    f"Snippets: {snippets_payload.get('status')} ({output_path})"
                )
                if snippets_payload.get("diff"):
                    console.print(str(snippets_payload["diff"]))
            console.print(summary)

        for error in errors:
            err_console.print(f"ERROR: {error.path}: {error.message}")
        for error in snippet_errors:
            err_console.print(f"ERROR: {target / 'README.md'}: {error}")
        if errors or snippet_errors:
            raise typer.Exit(code=1)

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
        console.print(
            f"Config: {'present' if report.config.get('present') else 'missing'}"
        )
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
        for error in report.pack.get("errors", []):
            console.print(f"- {error}")
        if not quiet:
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
