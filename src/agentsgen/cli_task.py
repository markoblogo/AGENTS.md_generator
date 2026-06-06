from __future__ import annotations

from pathlib import Path

import typer

from .cli_support import console, err_console, print_results, print_json, results_payload
from .task_loop import apply_task_evidence, apply_task_init, apply_task_verdict, task_dir
from .validators import validate_cli_task_response_payload


def register_task_commands(task_app: typer.Typer) -> None:
    @task_app.command("init")
    def task_init(
        task_id: str = typer.Argument(..., help="Stable task id, for example repomap-v2"),
        target: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
        title: str | None = typer.Option(None, "--title", help="Human-readable task title"),
        summary: str = typer.Option("Task contract captured by agentsgen.", "--summary", help="Short task summary"),
        acceptance: list[str] = typer.Option(None, "--acceptance", help="Acceptance criterion; repeat to add multiple items"),
        output: Path | None = typer.Option(None, "--output", help="Contract markdown path (default docs/ai/tasks/<task-id>/contract.md)"),
        format: str = typer.Option("text", "--format", help="Output format: text|json"),
        dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
    ):
        output_path = output or (task_dir(target, task_id) / "contract.md")
        try:
            results, payload = apply_task_init(target, task_id=task_id, title=title, summary=summary, acceptance=list(acceptance or []), output_path=output_path, dry_run=dry_run)
        except ValueError as exc:
            err_console.print(f"ERROR: {exc}")
            raise typer.Exit(code=1)
        response = {"version": 1, "command": "task init", "path": str(target), "output": str(output_path), "result": payload, "results": results_payload(results)}
        validate_cli_task_response_payload(response)
        errors = [row for row in results if row.action == "error"]
        if format == "json":
            print_json(response)
        else:
            print_results(results, print_diff=False)
            console.print(f"task_id: {payload['task_id']}")
            console.print(f"title: {payload['title']}")
            console.print(f"acceptance: {len(payload['acceptance'])}")
        if errors:
            raise typer.Exit(code=1)

    @task_app.command("evidence")
    def task_evidence(
        task_id: str = typer.Argument(..., help="Stable task id"),
        target: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
        check: list[str] = typer.Option(None, "--check", help="Check entry, for example pytest=passed"),
        artifact: list[str] = typer.Option(None, "--artifact", help="Artifact path; repeat to add multiple items"),
        note: list[str] = typer.Option(None, "--note", help="Evidence note; repeat to add multiple items"),
        output: Path | None = typer.Option(None, "--output", help="Evidence JSON path (default docs/ai/tasks/<task-id>/evidence.json)"),
        format: str = typer.Option("text", "--format", help="Output format: text|json"),
        dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
    ):
        output_path = output or (task_dir(target, task_id) / "evidence.json")
        try:
            results, payload = apply_task_evidence(target, task_id=task_id, checks=list(check or []), artifacts=list(artifact or []), notes=list(note or []), output_path=output_path, dry_run=dry_run)
        except ValueError as exc:
            err_console.print(f"ERROR: {exc}")
            raise typer.Exit(code=1)
        response = {"version": 1, "command": "task evidence", "path": str(target), "output": str(output_path), "result": payload, "results": results_payload(results)}
        validate_cli_task_response_payload(response)
        errors = [row for row in results if row.action == "error"]
        if format == "json":
            print_json(response)
        else:
            print_results(results, print_diff=False)
            console.print(f"task_id: {payload['task_id']}")
            console.print(f"checks: {len(payload['checks'])}")
            console.print(f"changed_files: {len(payload['changed_files'])}")
            console.print(f"evidence_status: {payload.get('evidence_status', 'unknown')}")
        if errors:
            raise typer.Exit(code=1)

    @task_app.command("verdict")
    def task_verdict(
        task_id: str = typer.Argument(..., help="Stable task id"),
        target: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
        status: str = typer.Option("needs-review", "--status", help="Verdict status: pass|fail|needs-review"),
        summary: str = typer.Option("Automated verdict captured by agentsgen.", "--summary", help="Short verdict summary"),
        blocking_item: list[str] = typer.Option(None, "--blocking-item", help="Blocking verdict item; repeat to add multiple entries"),
        output: Path | None = typer.Option(None, "--output", help="Verdict JSON path (default docs/ai/tasks/<task-id>/verdict.json)"),
        format: str = typer.Option("text", "--format", help="Output format: text|json"),
        dry_run: bool = typer.Option(False, "--dry-run", help="Do not write files"),
    ):
        output_path = output or (task_dir(target, task_id) / "verdict.json")
        try:
            results, payload = apply_task_verdict(target, task_id=task_id, status=status, summary=summary, blocking_items=list(blocking_item or []), output_path=output_path, dry_run=dry_run)
        except ValueError as exc:
            err_console.print(f"ERROR: {exc}")
            raise typer.Exit(code=1)
        response = {"version": 1, "command": "task verdict", "path": str(target), "output": str(output_path), "result": payload, "results": results_payload(results)}
        validate_cli_task_response_payload(response)
        errors = [row for row in results if row.action == "error"]
        if format == "json":
            print_json(response)
        else:
            print_results(results, print_diff=False)
            console.print(f"task_id: {payload['task_id']}")
            console.print(f"status: {payload['status']}")
            console.print(f"decision: {payload.get('decision', 'unknown')}")
            console.print(f"ready_for_apply: {payload.get('ready_for_apply', False)}")
            if payload["blocking_items"]:
                console.print(f"blocking_items: {len(payload['blocking_items'])}")
        if errors:
            raise typer.Exit(code=1)
