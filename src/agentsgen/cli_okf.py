from __future__ import annotations

import json
from pathlib import Path

import typer

from .cli_support import console, err_console
from .okf_export import export_okf_bundle, okf_results_payload


def register_okf_commands(app: typer.Typer) -> None:
    @app.command("export")
    def export(
        target: Path = typer.Argument(
            Path("."), exists=True, file_okay=False, dir_okay=True
        ),
        source_dir: str = typer.Option(
            "docs/ai", "--source-dir", help="Source AI docs directory"
        ),
        output_dir: str = typer.Option(
            "docs/ai/okf", "--output-dir", help="Output OKF bundle directory"
        ),
        check: bool = typer.Option(
            False,
            "--check",
            help="Validate that OKF export files are up to date (non-zero if drift is detected)",
        ),
        format: str = typer.Option("text", "--format", help="Output format: text|json"),
        dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
        print_diff: bool = typer.Option(
            False, "--print-diff", help="Print unified diff"
        ),
    ) -> None:
        """Generate an Open Knowledge Format bundle from docs/ai artifacts."""
        source_path = target / source_dir
        output_path = target / output_dir
        dry_run_effective = dry_run or check
        results = export_okf_bundle(
            target,
            source_dir=source_path,
            output_dir=output_path,
            dry_run=dry_run_effective,
            print_diff=print_diff,
        )
        errors = [row for row in results if row.action == "error"]
        drift = any(
            row.action in ("created", "updated") and row.changed for row in results
        )
        status = "ok"
        if errors:
            status = "error"
        elif check and drift:
            status = "drift"
        summary = (
            f"okf:{status} "
            f"(created={sum(1 for r in results if r.action == 'created')}, "
            f"updated={sum(1 for r in results if r.action == 'updated')}, "
            f"skipped={sum(1 for r in results if r.action == 'skipped')}, "
            f"errors={len(errors)})"
        )

        if format == "json":
            payload = {
                "status": status,
                "summary": summary,
                "check": check,
                "dry_run": dry_run_effective,
                "results": okf_results_payload(results),
            }
            raise typer.Exit(
                code=_emit_json(payload, status=status, check=check, drift=drift)
            )

        for row in results:
            console.print(f"{row.action}: {row.path} - {row.message}")
            if print_diff and row.diff:
                console.print(row.diff)
        console.print(summary)
        if errors:
            for row in errors:
                err_console.print(f"ERROR: {row.path}: {row.message}")
            raise typer.Exit(code=1)
        if check and drift:
            err_console.print(
                "OKF drift detected. Run `agentsgen okf export` to update generated files."
            )
            raise typer.Exit(code=1)


def _emit_json(
    payload: dict[str, object], *, status: str, check: bool, drift: bool
) -> int:
    import sys

    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    if status == "error":
        return 1
    if check and drift:
        return 1
    return 0
