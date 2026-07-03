from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from .cli_support import console
from .fleet import (
    build_fleet_scan_report,
    render_fleet_scan_markdown,
    write_fleet_scan_outputs,
)


def register_fleet_commands(app: typer.Typer) -> None:
    @app.command()
    def scan(
        root: list[Path] = typer.Argument(
            ..., exists=True, file_okay=False, dir_okay=True
        ),
        max_depth: int = typer.Option(
            2,
            "--max-depth",
            min=0,
            help="Max directory depth below each root",
        ),
        format: str = typer.Option("text", "--format", help="Output format: text|json"),
        out: Path | None = typer.Option(
            None, "--out", help="Write markdown report to this path"
        ),
        json_out: Path | None = typer.Option(
            None, "--json-out", help="Write JSON report to this path"
        ),
    ) -> None:
        """Scan many git repos and report agentsgen readiness without writes."""
        report = build_fleet_scan_report(root, max_depth=max_depth)
        write_fleet_scan_outputs(
            report,
            markdown_path=out,
            json_path=json_out,
        )

        if format == "json":
            sys.stdout.write(json.dumps(report, indent=2) + "\n")
        else:
            if out is None:
                console.print(render_fleet_scan_markdown(report))
            else:
                sys.stdout.write(f"markdown: {out}\n")
            if json_out is not None:
                sys.stdout.write(f"json: {json_out}\n")
