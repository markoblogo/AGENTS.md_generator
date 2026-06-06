from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from .actions import apply_pack, load_tool_config
from .cli_support import (
    console,
    err_console,
    interactive_init as _interactive_init,
    pack_plan_payload as _pack_plan_payload,
    parse_csv as _parse_csv,
    print_pack_plan as _print_pack_plan,
    print_pack_plan_header as _print_pack_plan_header,
    print_results as _print_results,
    resolve_repo_file as _resolve_repo_file,
    results_payload as _results_payload,
)
from .config import ToolConfig, merge_detect_hints
from .constants import CONFIG_FILENAME
from .detect import detect_repo
from .validators import (
    validate_cli_pack_plan_response_payload,
    validate_cli_pack_response_payload,
)
from .pack_engine import generate_readme_snippets


def register_pack_commands(app: typer.Typer) -> None:
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
            None,
            "--stack",
            help="Override stack for pack templates (python|node|static)",
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
        print_diff: bool = typer.Option(
            False, "--print-diff", help="Print unified diff"
        ),
        print_plan: bool = typer.Option(
            False, "--print-plan", help="Print dry pack plan (no file writes)"
        ),
    ):
        """Generate/update LLMO pack files with marker-safe updates."""
        cfg_path = target / ".agentsgen.json"
        try:
            cfg = load_tool_config(target) if cfg_path.exists() else ToolConfig()
        except Exception as exc:
            err_console.print(f"ERROR: Invalid {CONFIG_FILENAME}: {exc}")
            raise typer.Exit(code=1)

        if autodetect:
            det_cfg = ToolConfig.from_detect(detect_repo(target))
            existing_pack = cfg.pack
            cfg = merge_detect_hints(cfg, det_cfg)
            cfg.pack = existing_pack
        elif not cfg_path.exists():
            info = _interactive_init(
                target, defaults=True, stack_opt=stack, name_opt=None
            )
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
            r.action in ("created", "updated", "generated") and r.changed
            for r in results
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
                payload = {
                    "version": 1,
                    "status": status,
                    "summary": summary,
                    "check": check,
                    "dry_run": True,
                    "print_plan": True,
                    "plan": plan,
                }
                validate_cli_pack_plan_response_payload(payload)
                sys.stdout.write(
                    json.dumps(payload, indent=2)
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
            raise typer.Exit(code=0)

        if format == "json":
            payload = {
                "status": status,
                "summary": summary,
                "check": check,
                "dry_run": dry_run_effective,
                "results": _results_payload(results),
            }
            validate_cli_pack_response_payload(payload)
            sys.stdout.write(
                json.dumps(payload, indent=2)
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
            for error in errors:
                err_console.print(f"ERROR: {error.path}: {error.message}")
            raise typer.Exit(code=1)
        if check and drift:
            raise typer.Exit(code=1)

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
        print_diff: bool = typer.Option(
            False, "--print-diff", help="Print unified diff"
        ),
        format: str = typer.Option("text", "--format", help="Output format: text|json"),
    ):
        """Generate or validate README snippet extracts from AGENTSGEN snippet markers."""
        readme_path = _resolve_repo_file(target, readme, "README.md")
        output_path = _resolve_repo_file(
            target, output, "README_SNIPPETS.generated.md"
        )

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
