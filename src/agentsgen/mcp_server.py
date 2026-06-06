from __future__ import annotations

import json
from pathlib import Path

from .actions import aggregate_check, status_repo
from .detect import detect_repo
from .flow_ops import run_init_flow, run_pack_flow, run_update_flow
from .llm import LLMOptions
from .understand_context import build_understanding_payload
from .validators import (
    validate_mcp_init_response_payload,
    validate_mcp_check_response_payload,
    validate_mcp_detect_response_payload,
    validate_mcp_pack_response_payload,
    validate_mcp_status_response_payload,
    validate_mcp_understand_response_payload,
    validate_mcp_update_response_payload,
)

MCP_RESPONSE_VERSION = 1


def _json_safe(payload: dict[str, object]) -> dict[str, object]:
    return json.loads(json.dumps(payload))


def _results_payload(results: list[object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in results:
        rows.append(
            {
                "path": str(result.path),
                "action": result.action,
                "message": result.message,
                "changed": bool(result.changed),
                "diff": result.diff or "",
            }
        )
    return rows


def _status_and_summary(tool: str, results: list[object]) -> tuple[str, str]:
    errors = [row for row in results if row.action == "error"]
    created = sum(1 for row in results if row.action == "created")
    updated = sum(1 for row in results if row.action == "updated")
    generated = sum(1 for row in results if row.action == "generated")
    skipped = sum(1 for row in results if row.action == "skipped")
    status = "error" if errors else "ok"
    summary = (
        f"{tool}:{status} "
        f"(created={created}, updated={updated}, generated={generated}, "
        f"skipped={skipped}, errors={len(errors)})"
    )
    return status, summary


def _write_policy(*, dry_run: bool, check: bool = False, writes_applied: bool) -> dict[str, object]:
    mode = "check" if check else ("dry-run" if dry_run else "apply")
    payload = {
        "mode": mode,
        "may_write": mode == "apply",
        "writes_applied": bool(writes_applied and mode == "apply"),
    }
    return payload


def build_mcp_status_response(path: str = ".") -> dict[str, object]:
    repo_path = Path(path)
    payload = {
        "version": MCP_RESPONSE_VERSION,
        "tool": "status",
        "path": str(repo_path),
        "result": status_repo(repo_path).to_json(),
    }
    validate_mcp_status_response_payload(payload)
    return _json_safe(payload)


def build_mcp_check_response(path: str = ".") -> dict[str, object]:
    repo_path = Path(path)
    payload = {
        "version": MCP_RESPONSE_VERSION,
        "tool": "check",
        "path": str(repo_path),
        "result": aggregate_check(
            repo_path,
            pack_check=False,
            snippets_check=False,
        ).to_json(),
    }
    validate_mcp_check_response_payload(payload)
    return _json_safe(payload)


def build_mcp_detect_response(path: str = ".") -> dict[str, object]:
    repo_path = Path(path)
    payload = {
        "version": MCP_RESPONSE_VERSION,
        "tool": "detect",
        "path": str(repo_path),
        "result": detect_repo(repo_path).to_json(),
    }
    validate_mcp_detect_response_payload(payload)
    return _json_safe(payload)


def build_mcp_understand_response(
    path: str = ".",
    compact_budget_tokens: int = 4000,
) -> dict[str, object]:
    repo_path = Path(path)
    output_dir = repo_path / "docs" / "ai"
    payload = {
        "version": MCP_RESPONSE_VERSION,
        "tool": "understand",
        "path": str(repo_path),
        "output_dir": str(output_dir),
        "compact_budget_tokens": compact_budget_tokens,
        "result": build_understanding_payload(
            repo_path,
            output_dir=output_dir,
            compact_budget_tokens=compact_budget_tokens,
        ),
    }
    validate_mcp_understand_response_payload(payload)
    return _json_safe(payload)


def build_mcp_init_response(
    path: str = ".",
    *,
    stack: str = "",
    name: str = "",
    preset: str = "",
    autodetect: bool = True,
    force_config: bool = False,
    prompts: bool = True,
    dry_run: bool = False,
    llm_enabled: bool = False,
    llm_provider: str = "",
    llm_model: str = "",
    llm_timeout_seconds: int = 30,
) -> dict[str, object]:
    repo_path = Path(path)
    llm_options = LLMOptions(
        enabled=llm_enabled,
        provider=llm_provider,
        model=llm_model,
        timeout_seconds=llm_timeout_seconds,
    ).normalized()
    outcome = run_init_flow(
        repo_path,
        stack=stack or None,
        name=name or None,
        preset=preset or None,
        autodetect=autodetect,
        force_config=force_config,
        prompts=prompts,
        dry_run=dry_run,
        llm_options=llm_options,
    )
    status, summary = _status_and_summary("init", outcome.results)
    payload: dict[str, object] = {
        "version": MCP_RESPONSE_VERSION,
        "tool": "init",
        "path": str(repo_path),
        "config_path": str(repo_path / ".agentsgen.json"),
        "config_written": outcome.config_written,
        "status": status,
        "summary": summary,
        "dry_run": dry_run,
        "write_policy": _write_policy(
            dry_run=dry_run,
            writes_applied=outcome.config_written or any(row.changed for row in outcome.results),
        ),
        "llm": {
            "request": llm_options.to_json(),
            "result": outcome.llm_result.to_json() if outcome.llm_result else None,
        }
        if llm_options.enabled
        else None,
        "results": _results_payload(outcome.results),
    }
    validate_mcp_init_response_payload(payload)
    return _json_safe(payload)


def build_mcp_update_response(
    path: str = ".",
    *,
    dry_run: bool = False,
    llm_enabled: bool = False,
    llm_provider: str = "",
    llm_model: str = "",
    llm_timeout_seconds: int = 30,
) -> dict[str, object]:
    repo_path = Path(path)
    llm_options = LLMOptions(
        enabled=llm_enabled,
        provider=llm_provider,
        model=llm_model,
        timeout_seconds=llm_timeout_seconds,
    ).normalized()
    results, llm_result = run_update_flow(
        repo_path,
        dry_run=dry_run,
        llm_options=llm_options,
    )
    status, summary = _status_and_summary("update", results)
    payload: dict[str, object] = {
        "version": MCP_RESPONSE_VERSION,
        "tool": "update",
        "path": str(repo_path),
        "status": status,
        "summary": summary,
        "dry_run": dry_run,
        "write_policy": _write_policy(
            dry_run=dry_run,
            writes_applied=any(row.changed for row in results),
        ),
        "llm": {
            "request": llm_options.to_json(),
            "result": llm_result.to_json() if llm_result else None,
        }
        if llm_options.enabled
        else None,
        "results": _results_payload(results),
    }
    validate_mcp_update_response_payload(payload)
    return _json_safe(payload)


def build_mcp_pack_response(
    path: str = ".",
    *,
    autodetect: bool = True,
    stack: str = "",
    llms_format: str = "",
    output_dir: str = "",
    files: list[str] | None = None,
    site: str = "",
    check: bool = False,
    dry_run: bool = False,
) -> dict[str, object]:
    repo_path = Path(path)
    outcome = run_pack_flow(
        repo_path,
        autodetect=autodetect,
        stack=stack or None,
        llms_format=llms_format or None,
        output_dir=output_dir or None,
        files=files,
        site=site or None,
        check=check,
        dry_run=dry_run,
    )
    payload = {
        "version": MCP_RESPONSE_VERSION,
        "tool": "pack",
        "path": str(repo_path),
        "status": outcome.status,
        "summary": outcome.summary,
        "dry_run": outcome.dry_run,
        "check": outcome.check,
        "drift": outcome.drift,
        "write_policy": _write_policy(
            dry_run=outcome.dry_run,
            check=outcome.check,
            writes_applied=any(row.changed for row in outcome.results),
        ),
        "results": _results_payload(outcome.results),
    }
    validate_mcp_pack_response_payload(payload)
    return _json_safe(payload)


def serve_stdio() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "MCP support requires the optional dependency group: pip install '.[mcp]'"
        ) from exc

    server = FastMCP("agentsgen")

    @server.tool()
    def status(path: str = ".") -> dict[str, object]:
        return build_mcp_status_response(path)

    @server.tool()
    def check(path: str = ".") -> dict[str, object]:
        return build_mcp_check_response(path)

    @server.tool()
    def detect(path: str = ".") -> dict[str, object]:
        return build_mcp_detect_response(path)

    @server.tool()
    def understand(path: str = ".", compact_budget_tokens: int = 4000) -> dict[str, object]:
        return build_mcp_understand_response(
            path=path,
            compact_budget_tokens=compact_budget_tokens,
        )

    @server.tool()
    def init(
        path: str = ".",
        stack: str = "",
        name: str = "",
        preset: str = "",
        autodetect: bool = True,
        force_config: bool = False,
        prompts: bool = True,
        dry_run: bool = False,
        llm_enabled: bool = False,
        llm_provider: str = "",
        llm_model: str = "",
        llm_timeout_seconds: int = 30,
    ) -> dict[str, object]:
        return build_mcp_init_response(
            path=path,
            stack=stack,
            name=name,
            preset=preset,
            autodetect=autodetect,
            force_config=force_config,
            prompts=prompts,
            dry_run=dry_run,
            llm_enabled=llm_enabled,
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_timeout_seconds=llm_timeout_seconds,
        )

    @server.tool()
    def update(
        path: str = ".",
        dry_run: bool = False,
        llm_enabled: bool = False,
        llm_provider: str = "",
        llm_model: str = "",
        llm_timeout_seconds: int = 30,
    ) -> dict[str, object]:
        return build_mcp_update_response(
            path=path,
            dry_run=dry_run,
            llm_enabled=llm_enabled,
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_timeout_seconds=llm_timeout_seconds,
        )

    @server.tool()
    def pack(
        path: str = ".",
        autodetect: bool = True,
        stack: str = "",
        llms_format: str = "",
        output_dir: str = "",
        files: list[str] | None = None,
        site: str = "",
        check: bool = False,
        dry_run: bool = False,
    ) -> dict[str, object]:
        return build_mcp_pack_response(
            path=path,
            autodetect=autodetect,
            stack=stack,
            llms_format=llms_format,
            output_dir=output_dir,
            files=files,
            site=site,
            check=check,
            dry_run=dry_run,
        )

    server.run()
