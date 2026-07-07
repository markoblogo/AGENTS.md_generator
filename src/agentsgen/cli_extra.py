from __future__ import annotations

from pathlib import Path

import typer

from .analyze import apply_analysis
from .cli_support import (
    console,
    err_console,
    print_json,
    print_results,
    resolve_repo_file,
    results_payload,
)
from .detect import detect_repo
from .mcp_server import serve_stdio
from .meta import apply_metadata
from .rabbithole_seed import write_rabbithole_seed
from .understand_context import apply_understanding
from .validators import (
    validate_cli_analyze_response_payload,
    validate_cli_meta_response_payload,
    validate_cli_understand_response_payload,
    validate_detect_result_payload,
)


def register_extra_commands(app: typer.Typer) -> None:
    @app.command()
    def rabbithole_seed(
        target: Path = typer.Argument(
            Path("."), exists=True, file_okay=False, dir_okay=True
        ),
        output: Path | None = typer.Option(
            None,
            "--output",
            help="Output markdown file (default docs/ai/rabbithole.seed.md)",
        ),
        max_chars_per_file: int = typer.Option(
            6000,
            "--max-chars-per-file",
            min=512,
            help="Maximum excerpt size per source file",
        ),
        dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
        format: str = typer.Option("text", "--format", help="Output format: text|json"),
    ):
        result = write_rabbithole_seed(
            target,
            output_path=output,
            max_chars_per_file=max_chars_per_file,
            dry_run=dry_run,
        )
        payload = {
            "version": 1,
            "command": "rabbithole-seed",
            "path": str(target),
            "output": str(result.output_path),
            "dry_run": result.dry_run,
            "source_files": result.source_files,
        }
        if format == "json":
            print_json(payload)
            return
        action = "would_write" if dry_run else "wrote"
        console.print(f"{action}: {result.output_path}")
        console.print(f"source_files: {len(result.source_files)}")

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
        focus: str | None = typer.Option(
            None,
            "--focus",
            help="Limit compact repomap and relevance ranking to files matching this path/content query and nearby imports",
        ),
        changed: bool = typer.Option(
            False,
            "--changed",
            help="Limit compact repomap and relevance ranking to changed files and nearby imports",
        ),
    ):
        out_dir = Path(output_dir)
        if not out_dir.is_absolute():
            out_dir = target / out_dir
        results, payload = apply_understanding(
            target,
            output_dir=out_dir,
            compact_budget_tokens=compact_budget,
            focus=focus,
            changed_only=changed,
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
            "slice": payload["knowledge"].get("slice", {}),
            "relevance": payload["knowledge"].get("relevance", []),
            "results": results_payload(results),
        }
        validate_cli_understand_response_payload(response)
        if format == "json":
            print_json(response)
        else:
            print_results(results, print_diff=False)
            console.print(f"stack: {payload['stack']}")
            console.print(
                "summary: "
                f"files={payload['summary']['files_count']} "
                f"edges={payload['summary']['edges_count']} "
                f"entrypoints={payload['summary']['entrypoints_count']} "
                f"changed={payload['summary']['changed_files_count']} "
                f"compact_budget={payload['summary']['compact_budget_tokens']} "
                f"slice={payload['summary']['slice_files_count']}"
            )
            if payload["summary"]["focus"]:
                console.print(f"focus: {payload['summary']['focus']}")
            if payload["summary"]["changed_only"]:
                console.print("mode: changed")
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
            None, "--output", help="Output JSON file (default docs/ai/llmo-score.json)"
        ),
        use_ai: bool = typer.Option(
            False,
            "--use-ai",
            help="Add an advisory OpenAI review (requires OPENAI_API_KEY)",
        ),
        dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
    ):
        output_path = resolve_repo_file(target, output, "docs/ai/llmo-score.json")
        try:
            results, payload = apply_analysis(
                target, url=url, output_path=output_path, use_ai=use_ai, dry_run=dry_run
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
            "results": results_payload(results),
        }
        validate_cli_analyze_response_payload(response)
        if format == "json":
            print_json(response)
        else:
            print_results(results, print_diff=False)
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
            None, "--output", help="Output JSON file (default docs/ai/llmo-meta.json)"
        ),
        dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
    ):
        output_path = resolve_repo_file(target, output, "docs/ai/llmo-meta.json")
        try:
            results, payload = apply_metadata(
                target, url=url, output_path=output_path, dry_run=dry_run
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
            "results": results_payload(results),
        }
        validate_cli_meta_response_payload(response)
        if format == "json":
            print_json(response)
        else:
            print_results(results, print_diff=False)
            console.print(f"url: {payload['url']}")
            console.print(f"title: {payload['result']['title']}")
            console.print(f"description: {payload['result']['description']}")
            if payload["result"]["keywords"]:
                console.print("keywords: " + ", ".join(payload["result"]["keywords"]))
        if errors:
            raise typer.Exit(code=1)

    @app.command()
    def detect(
        repo: Path = typer.Argument(
            Path("."), exists=True, file_okay=False, dir_okay=True
        ),
        format: str = typer.Option("text", "--format", help="Output format: text|json"),
        explain: bool = typer.Option(
            False,
            "--explain",
            help="Print rationale (why detection chose these values)",
        ),
    ):
        det = detect_repo(repo)
        validate_detect_result_payload(det.to_json())
        if format == "json":
            print_json(det.to_json())
            raise typer.Exit(code=0)
        console.print(f"primary_stack: {det.project.get('primary_stack')}")
        if det.commands:
            console.print("commands:")
            for key in sorted(det.commands.keys()):
                console.print(f"- {key}: {det.commands[key]}")
        else:
            console.print("commands: (none)")
        if explain and det.rationale:
            console.print("rationale:")
            for item in det.rationale:
                console.print(f"- {item}")
        console.print("evidence:")
        for key, value in det.to_json().get("evidence", {}).items():
            if value:
                console.print(f"- {key}: {', '.join(value)}")

    @app.command()
    def mcp() -> None:
        try:
            serve_stdio()
        except RuntimeError as exc:
            err_console.print(f"ERROR: {exc}")
            raise typer.Exit(code=1)
