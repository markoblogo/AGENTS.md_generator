from __future__ import annotations

from pathlib import Path
from typing import cast

import typer

from .cli_support import print_json, print_results, results_payload
from .reflect_sessions import apply_reflect_sessions
from .validators import validate_cli_reflect_sessions_response_payload


def register_reflect_commands(app: typer.Typer) -> None:
    @app.command("sessions")
    def sessions(
        target: Path = typer.Argument(
            Path("."), exists=True, file_okay=False, dir_okay=True
        ),
        format: str = typer.Option("text", "--format", help="Output format: text|json"),
        output_dir: str = typer.Option(
            "docs/ai", "--output-dir", help="Where to write reflect artifacts"
        ),
        codex_root: Path = typer.Option(
            Path.home() / ".codex" / "sessions",
            "--codex-root",
            help="Codex session root to scan",
        ),
        dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
        print_diff: bool = typer.Option(
            False, "--print-diff", help="Print unified diff"
        ),
    ) -> None:
        out_dir = Path(output_dir)
        if not out_dir.is_absolute():
            out_dir = target / out_dir
        results, sessions_payload, signals_payload = apply_reflect_sessions(
            target,
            codex_root=codex_root,
            output_dir=out_dir,
            dry_run=dry_run,
            print_diff=print_diff,
        )
        summary = cast(dict[str, object], signals_payload["summary"])
        response = {
            "version": 1,
            "command": "reflect sessions",
            "path": str(target),
            "output_dir": str(out_dir),
            "source": {"tool": "codex", "root": str(codex_root)},
            "summary": summary,
            "outputs": {
                "sessions_json": str(out_dir / "agent-sessions.json"),
                "signals_json": str(out_dir / "agent-signals.json"),
                "patterns_md": str(out_dir / "agent-patterns.md"),
            },
            "results": results_payload(results),
        }
        validate_cli_reflect_sessions_response_payload(response)
        if format == "json":
            print_json(response)
            return
        print_results(results, print_diff=print_diff)
        typer.echo(
            "reflect: "
            f"sessions={cast(int, summary['session_count'])} "
            f"prompts={cast(int, summary['prompt_count'])} "
            f"plan_first={cast(int, summary['plan_first_ratio'])}% "
            f"redirects={cast(int, summary['redirect_count'])}"
        )
