from __future__ import annotations

from typing import Any


Schema = dict[str, Any]

SCHEMA_FORMAT_VERSION = 1


def _string(*, enum: list[str] | None = None, nullable: bool = False) -> Schema:
    schema: Schema = {"type": "string"}
    if enum:
        schema["enum"] = list(enum)
    if nullable:
        schema["nullable"] = True
    return schema


def _integer(*, nullable: bool = False) -> Schema:
    schema: Schema = {"type": "integer"}
    if nullable:
        schema["nullable"] = True
    return schema


def _boolean() -> Schema:
    return {"type": "boolean"}


def _array(items: Schema) -> Schema:
    return {"type": "array", "items": items}


def _object(
    *,
    properties: dict[str, Schema],
    required: list[str],
    additional_properties: bool = True,
    nullable: bool = False,
) -> Schema:
    schema: Schema = {
        "type": "object",
        "required": list(required),
        "properties": dict(properties),
        "additional_properties": additional_properties,
    }
    if nullable:
        schema["nullable"] = True
    return schema


def _named(name: str, version: int, schema: Schema) -> Schema:
    return {
        "schema_format_version": SCHEMA_FORMAT_VERSION,
        "name": name,
        "version": version,
        "schema": schema,
    }


FILE_RESULT_SCHEMA = _named(
    "file-result",
    1,
    _object(
        properties={
            "path": _string(),
            "action": _string(),
            "message": _string(),
            "changed": _boolean(),
            "diff": _string(),
        },
        required=["path", "action", "message", "changed", "diff"],
    ),
)


DETECT_RESULT_SCHEMA = _named(
    "detect-result",
    1,
    _object(
        properties={
            "project": _object(properties={}, required=[]),
            "paths": _object(properties={}, required=[]),
            "commands": _object(properties={}, required=[]),
            "evidence": _object(
                properties={
                    "python": _array(_string()),
                    "node": _array(_string()),
                    "make": _array(_string()),
                    "ci": _array(_string()),
                },
                required=["python", "node", "make", "ci"],
            ),
            "rationale": _array(_string()),
        },
        required=["project", "paths", "commands", "evidence", "rationale"],
    ),
)


ENTRYPOINTS_SCHEMA = _named(
    "agents.entrypoints",
    1,
    _object(
        properties={
            "version": _integer(),
            "generated_by": _string(),
            "generated_at": _string(),
            "repo": _object(
                properties={
                    "path": _string(),
                    "stack": _string(),
                    "autodetect": _boolean(),
                },
                required=["path", "stack", "autodetect"],
            ),
            "commands": _array(
                _object(
                    properties={
                        "id": _string(),
                        "title": _string(),
                        "command": _string(),
                        "cwd": _string(),
                        "source": _object(
                            properties={"kind": _string(), "hint": _string()},
                            required=["kind", "hint"],
                        ),
                        "notes": _string(),
                    },
                    required=["id", "title", "command", "cwd", "source", "notes"],
                )
            ),
        },
        required=["version", "generated_by", "generated_at", "repo", "commands"],
    ),
)


KNOWLEDGE_SCHEMA = _named(
    "agents.knowledge",
    1,
    _object(
        properties={
            "version": _integer(),
            "repo_path": _string(),
            "generated_at": _string(),
            "files": _array(
                _object(
                    properties={
                        "path": _string(),
                        "size": _integer(),
                        "language": _string(),
                        "symbols_count": _integer(),
                    },
                    required=["path", "size", "language", "symbols_count"],
                )
            ),
            "edges": _array(
                _object(
                    properties={
                        "from": _string(),
                        "to": _string(),
                        "kind": _string(),
                    },
                    required=["from", "to", "kind"],
                )
            ),
            "entrypoints": _array(
                _object(
                    properties={
                        "label": _string(),
                        "command": _string(),
                        "source": _string(),
                    },
                    required=["label", "command", "source"],
                )
            ),
            "changed_files": _array(_string()),
            "entrypoint_files": _array(_string()),
            "slice": _object(
                properties={
                    "focus": _string(nullable=True),
                    "focus_matches": _array(_string()),
                    "changed_only": _boolean(),
                    "changed_matches": _array(_string()),
                },
                required=["focus_matches", "changed_only", "changed_matches"],
            ),
            "relevance": _array(
                _object(
                    properties={
                        "path": _string(),
                        "score": _integer(),
                        "signals": _array(_string()),
                        "distance_from_entrypoint": _integer(nullable=True),
                        "changed": _boolean(),
                        "entrypoint": _boolean(),
                    },
                    required=["path", "score", "signals", "changed", "entrypoint"],
                )
            ),
        },
        required=[
            "version",
            "repo_path",
            "generated_at",
            "files",
            "edges",
            "entrypoints",
            "changed_files",
            "entrypoint_files",
            "slice",
            "relevance",
        ],
    ),
)


ID_CONTEXT_SCHEMA = _named(
    "id-context",
    1,
    _object(
        properties={
            "version": _integer(),
            "generated_by": _string(),
            "generated_at": _string(),
            "repo": _object(
                properties={
                    "name": _string(),
                    "path": _string(),
                    "stack": _string(),
                    "autodetect": _boolean(),
                },
                required=["name", "path", "stack", "autodetect"],
            ),
            "handoff": _object(
                properties={
                    "consumer": _string(),
                    "target": _string(),
                    "status": _string(),
                    "purpose": _string(),
                },
                required=["consumer", "target", "status", "purpose"],
            ),
            "bundle": _object(
                properties={
                    "repo_docs": _object(
                        properties={"agents_md": _string(), "runbook_md": _string()},
                        required=["agents_md", "runbook_md"],
                    ),
                    "pack": _object(
                        properties={
                            "llms": _string(),
                            "entrypoints": _string(),
                            "id_context": _string(),
                            "how_to_run": _string(),
                            "how_to_test": _string(),
                            "architecture": _string(),
                            "data_contracts": _string(),
                            "security": _string(),
                            "contributing": _string(),
                            "readme_snippets": _string(),
                        },
                        required=[
                            "llms",
                            "entrypoints",
                            "id_context",
                            "how_to_run",
                            "how_to_test",
                            "architecture",
                            "data_contracts",
                            "security",
                            "contributing",
                            "readme_snippets",
                        ],
                    ),
                    "optional_repo_artifacts": _object(
                        properties={
                            "repomap": _string(),
                            "repomap_compact": _string(),
                            "graph": _string(),
                            "knowledge": _string(),
                            "proof_tasks_dir": _string(),
                        },
                        required=[
                            "repomap",
                            "repomap_compact",
                            "graph",
                            "knowledge",
                            "proof_tasks_dir",
                        ],
                    ),
                },
                required=["repo_docs", "pack", "optional_repo_artifacts"],
            ),
            "usage": _object(
                properties={
                    "preferred_inputs": _array(_string()),
                    "notes": _array(_string()),
                },
                required=["preferred_inputs", "notes"],
            ),
        },
        required=[
            "version",
            "generated_by",
            "generated_at",
            "repo",
            "handoff",
            "bundle",
            "usage",
        ],
    ),
)


TASK_CONTRACT_SCHEMA = _named(
    "task.contract",
    1,
    _object(
        properties={
            "version": _integer(),
            "generated_by": _string(),
            "generated_at": _string(),
            "task_id": _string(),
            "title": _string(),
            "summary": _string(),
            "acceptance": _array(_string()),
            "path": _string(),
        },
        required=[
            "version",
            "generated_by",
            "generated_at",
            "task_id",
            "title",
            "summary",
            "acceptance",
            "path",
        ],
    ),
)


TASK_EVIDENCE_SCHEMA = _named(
    "task.evidence",
    2,
    _object(
        properties={
            "version": _integer(),
            "generated_by": _string(),
            "generated_at": _string(),
            "task_id": _string(),
            "checks": _array(
                _object(
                    properties={
                        "name": _string(),
                        "status": _string(),
                        "required": _boolean(),
                        "kind": _string(),
                    },
                    required=["name", "status", "required", "kind"],
                )
            ),
            "check_summary": _object(
                properties={
                    "total": _integer(),
                    "passed": _integer(),
                    "failed": _integer(),
                    "pending": _integer(),
                    "recorded": _integer(),
                },
                required=["total", "passed", "failed", "pending", "recorded"],
            ),
            "changed_files": _array(_string()),
            "changed_files_count": _integer(),
            "artifacts": _array(_string()),
            "artifact_details": _array(
                _object(
                    properties={
                        "path": _string(),
                        "kind": _string(),
                        "present": _boolean(),
                    },
                    required=["path", "kind", "present"],
                )
            ),
            "artifact_summary": _object(
                properties={
                    "total": _integer(),
                    "present": _integer(),
                    "missing": _integer(),
                },
                required=["total", "present", "missing"],
            ),
            "contract_present": _boolean(),
            "evidence_status": _string(),
            "repo_state": _object(
                properties={
                    "git_available": _boolean(),
                    "working_tree_dirty": _boolean(),
                },
                required=["git_available", "working_tree_dirty"],
            ),
            "notes": _array(_string()),
        },
        required=[
            "version",
            "generated_by",
            "generated_at",
            "task_id",
            "checks",
            "check_summary",
            "changed_files",
            "changed_files_count",
            "artifacts",
            "artifact_details",
            "artifact_summary",
            "contract_present",
            "evidence_status",
            "repo_state",
            "notes",
        ],
    ),
)


TASK_VERDICT_SCHEMA = _named(
    "task.verdict",
    2,
    _object(
        properties={
            "version": _integer(),
            "generated_by": _string(),
            "generated_at": _string(),
            "task_id": _string(),
            "status": _string(enum=["pass", "fail", "needs-review"]),
            "summary": _string(),
            "blocking_items": _array(_string()),
            "blocking_details": _array(
                _object(
                    properties={
                        "message": _string(),
                        "severity": _string(),
                        "blocks_apply": _boolean(),
                    },
                    required=["message", "severity", "blocks_apply"],
                )
            ),
            "evidence_status": _string(),
            "check_summary": _object(
                properties={},
                required=[],
            ),
            "artifact_summary": _object(
                properties={},
                required=[],
            ),
            "review_ready": _boolean(),
            "ready_for_apply": _boolean(),
            "decision": _string(),
            "recommendation": _string(),
        },
        required=[
            "version",
            "generated_by",
            "generated_at",
            "task_id",
            "status",
            "summary",
            "blocking_items",
            "blocking_details",
            "evidence_status",
            "check_summary",
            "artifact_summary",
            "review_ready",
            "ready_for_apply",
            "decision",
            "recommendation",
        ],
    ),
)


AGGREGATED_CHECK_SCHEMA = _named(
    "aggregated-check-report",
    1,
    _object(
        properties={
            "version": _integer(),
            "command": _string(),
            "path": _string(),
            "status": _string(),
            "checks": _object(
                properties={
                    "core": _object(
                        properties={
                            "status": _string(),
                            "drift_count": _integer(),
                            "error_count": _integer(),
                            "warnings_count": _integer(),
                            "results": _array(
                                _object(
                                    properties={
                                        "level": _string(),
                                        "message": _string(),
                                    },
                                    required=["level", "message"],
                                )
                            ),
                            "raw": _object(
                                properties={
                                    "exit_code": _integer(),
                                    "problems": _array(_string()),
                                    "warnings": _array(_string()),
                                },
                                required=["exit_code", "problems", "warnings"],
                            ),
                        },
                        required=[
                            "status",
                            "drift_count",
                            "error_count",
                            "warnings_count",
                            "results",
                            "raw",
                        ],
                    ),
                    "pack": _object(
                        properties={
                            "status": _string(),
                            "drift_count": _integer(),
                            "error_count": _integer(),
                            "raw": _object(
                                properties={
                                    "status": _string(),
                                    "summary": _string(),
                                    "check": _boolean(),
                                    "dry_run": _boolean(),
                                    "results": _array(FILE_RESULT_SCHEMA["schema"]),
                                },
                                required=[
                                    "status",
                                    "summary",
                                    "check",
                                    "dry_run",
                                    "results",
                                ],
                            ),
                            "reason": _string(),
                        },
                        required=["status", "drift_count", "error_count", "raw"],
                        nullable=True,
                    ),
                    "snippets": _object(
                        properties={
                            "status": _string(),
                            "drift_count": _integer(),
                            "error_count": _integer(),
                            "raw": _object(
                                properties={
                                    "status": _string(),
                                    "check": _boolean(),
                                    "dry_run": _boolean(),
                                    "format_version": _integer(),
                                    "readme_path": _string(),
                                    "output_path": _string(),
                                    "snippets_count": _integer(),
                                    "snippets": _array(
                                        _object(
                                            properties={
                                                "name": _string(),
                                                "start_line": _integer(),
                                                "end_line": _integer(),
                                                "content": _string(),
                                            },
                                            required=[
                                                "name",
                                                "start_line",
                                                "end_line",
                                                "content",
                                            ],
                                        )
                                    ),
                                    "diff": _string(),
                                    "message": _string(),
                                },
                                required=[
                                    "status",
                                    "check",
                                    "dry_run",
                                    "format_version",
                                    "readme_path",
                                    "output_path",
                                    "snippets_count",
                                    "snippets",
                                ],
                            ),
                            "reason": _string(),
                        },
                        required=["status", "drift_count", "error_count", "raw"],
                        nullable=True,
                    ),
                },
                required=["core", "pack", "snippets"],
            ),
            "summary": _object(
                properties={
                    "ok": _boolean(),
                    "drift_count": _integer(),
                    "error_count": _integer(),
                    "skipped_count": _integer(),
                },
                required=["ok", "drift_count", "error_count", "skipped_count"],
            ),
        },
        required=["version", "command", "path", "status", "checks", "summary"],
    ),
)


REPO_STATUS_SCHEMA = _named(
    "repo-status-report",
    1,
    _object(
        properties={
            "status": _string(),
            "path": _string(),
            "config": _object(
                properties={"present": _boolean()},
                required=["present"],
            ),
            "agents_md": _object(
                properties={
                    "present": _boolean(),
                    "markers": _boolean(),
                    "marker_sections": _integer(),
                    "generated_sibling": _boolean(),
                },
                required=["present", "markers", "marker_sections", "generated_sibling"],
            ),
            "runbook_md": _object(
                properties={
                    "present": _boolean(),
                    "markers": _boolean(),
                    "marker_sections": _integer(),
                    "generated_sibling": _boolean(),
                },
                required=["present", "markers", "marker_sections", "generated_sibling"],
            ),
            "pack": _object(
                properties={
                    "status": _string(),
                    "findings": _array(_string()),
                    "errors": _array(_string()),
                },
                required=["status", "findings", "errors"],
            ),
            "generated": _object(
                properties={
                    "count": _integer(),
                    "files": _array(_string()),
                },
                required=["count", "files"],
            ),
            "summary": _object(
                properties={"drift": _integer(), "errors": _integer()},
                required=["drift", "errors"],
            ),
        },
        required=[
            "status",
            "path",
            "config",
            "agents_md",
            "runbook_md",
            "pack",
            "generated",
            "summary",
        ],
    ),
)


UNDERSTAND_PAYLOAD_SCHEMA = _named(
    "understand-payload",
    1,
    _object(
        properties={
            "stack": _string(),
            "repomap": _string(),
            "compact_repomap": _string(),
            "graph": _string(),
            "knowledge": KNOWLEDGE_SCHEMA["schema"],
            "summary": _object(
                properties={
                    "files_count": _integer(),
                    "edges_count": _integer(),
                    "entrypoints_count": _integer(),
                    "changed_files_count": _integer(),
                    "compact_budget_tokens": _integer(),
                    "focus": _string(nullable=True),
                    "changed_only": _boolean(),
                    "slice_files_count": _integer(),
                },
                required=[
                    "files_count",
                    "edges_count",
                    "entrypoints_count",
                    "changed_files_count",
                    "compact_budget_tokens",
                    "focus",
                    "changed_only",
                    "slice_files_count",
                ],
            ),
        },
        required=[
            "stack",
            "repomap",
            "compact_repomap",
            "graph",
            "knowledge",
            "summary",
        ],
    ),
)


ANALYSIS_PAYLOAD_SCHEMA = _named(
    "analysis-payload",
    1,
    _object(
        properties={
            "version": _integer(),
            "generated_by": _string(),
            "generated_at": _string(),
            "url": _string(),
            "final_url": _string(),
            "mode": _string(),
            "score": _integer(),
            "visibility": _string(),
            "summary": _string(),
            "factors": _object(properties={}, required=[]),
            "evidence": _object(properties={}, required=[]),
            "recommendations": _array(_string()),
            "ai_review": _string(),
        },
        required=[
            "version",
            "generated_by",
            "generated_at",
            "url",
            "final_url",
            "mode",
            "score",
            "visibility",
            "summary",
            "factors",
            "evidence",
            "recommendations",
        ],
    ),
)


METADATA_PAYLOAD_SCHEMA = _named(
    "metadata-payload",
    1,
    _object(
        properties={
            "version": _integer(),
            "generated_by": _string(),
            "generated_at": _string(),
            "url": _string(),
            "final_url": _string(),
            "mode": _string(),
            "result": _object(
                properties={
                    "title": _string(),
                    "description": _string(),
                    "keywords": _array(_string()),
                    "shortDescription": _string(),
                },
                required=["title", "description", "keywords", "shortDescription"],
            ),
        },
        required=[
            "version",
            "generated_by",
            "generated_at",
            "url",
            "final_url",
            "mode",
            "result",
        ],
    ),
)


CLI_UNDERSTAND_RESPONSE_SCHEMA = _named(
    "cli-understand-response",
    1,
    _object(
        properties={
            "version": _integer(),
            "command": _string(),
            "path": _string(),
            "output_dir": _string(),
            "stack": _string(),
            "summary": UNDERSTAND_PAYLOAD_SCHEMA["schema"]["properties"]["summary"],
            "changed_files": _array(_string()),
            "slice": KNOWLEDGE_SCHEMA["schema"]["properties"]["slice"],
            "relevance": KNOWLEDGE_SCHEMA["schema"]["properties"]["relevance"],
            "results": _array(FILE_RESULT_SCHEMA["schema"]),
        },
        required=[
            "version",
            "command",
            "path",
            "output_dir",
            "stack",
            "summary",
            "changed_files",
            "slice",
            "relevance",
            "results",
        ],
    ),
)


CLI_ANALYZE_RESPONSE_SCHEMA = _named(
    "cli-analyze-response",
    1,
    _object(
        properties={
            "version": _integer(),
            "command": _string(),
            "path": _string(),
            "output": _string(),
            "result": ANALYSIS_PAYLOAD_SCHEMA["schema"],
            "results": _array(FILE_RESULT_SCHEMA["schema"]),
        },
        required=["version", "command", "path", "output", "result", "results"],
    ),
)


CLI_META_RESPONSE_SCHEMA = _named(
    "cli-meta-response",
    1,
    _object(
        properties={
            "version": _integer(),
            "command": _string(),
            "path": _string(),
            "output": _string(),
            "result": METADATA_PAYLOAD_SCHEMA["schema"],
            "results": _array(FILE_RESULT_SCHEMA["schema"]),
        },
        required=["version", "command", "path", "output", "result", "results"],
    ),
)


CLI_TASK_RESPONSE_SCHEMA = _named(
    "cli-task-response",
    1,
    _object(
        properties={
            "version": _integer(),
            "command": _string(),
            "path": _string(),
            "output": _string(),
            "result": _object(properties={}, required=[]),
            "results": _array(FILE_RESULT_SCHEMA["schema"]),
        },
        required=["version", "command", "path", "output", "result", "results"],
    ),
)


CLI_PACK_RESPONSE_SCHEMA = _named(
    "cli-pack-response",
    1,
    _object(
        properties={
            "status": _string(),
            "summary": _string(),
            "check": _boolean(),
            "dry_run": _boolean(),
            "results": _array(FILE_RESULT_SCHEMA["schema"]),
        },
        required=["status", "summary", "check", "dry_run", "results"],
    ),
)


CLI_PACK_PLAN_RESPONSE_SCHEMA = _named(
    "cli-pack-plan-response",
    1,
    _object(
        properties={
            "version": _integer(),
            "status": _string(),
            "summary": _string(),
            "check": _boolean(),
            "dry_run": _boolean(),
            "print_plan": _boolean(),
            "plan": _array(
                _object(
                    properties={
                        "path": _string(),
                        "action": _string(),
                        "sections": _array(_string()),
                        "message": _string(),
                    },
                    required=["path", "action", "sections", "message"],
                )
            ),
        },
        required=[
            "version",
            "status",
            "summary",
            "check",
            "dry_run",
            "print_plan",
            "plan",
        ],
    ),
)


LLM_OPTIONS_SCHEMA = _named(
    "llm-options",
    1,
    _object(
        properties={
            "enabled": _boolean(),
            "provider": _string(),
            "model": _string(),
            "timeout_seconds": _integer(),
            "narrative_sections": _array(_string()),
        },
        required=[
            "enabled",
            "provider",
            "model",
            "timeout_seconds",
            "narrative_sections",
        ],
    ),
)


LLM_ENHANCEMENT_RESULT_SCHEMA = _named(
    "llm-enhancement-result",
    1,
    _object(
        properties={
            "provider": _string(),
            "applied": _boolean(),
            "sections": _object(properties={}, required=[]),
            "message": _string(),
        },
        required=["provider", "applied", "sections", "message"],
    ),
)


WRITE_POLICY_SCHEMA = _named(
    "write-policy",
    1,
    _object(
        properties={
            "mode": _string(),
            "may_write": _boolean(),
            "writes_applied": _boolean(),
        },
        required=["mode", "may_write", "writes_applied"],
    ),
)


MCP_STATUS_RESPONSE_SCHEMA = _named(
    "mcp-status-response",
    1,
    _object(
        properties={
            "version": _integer(),
            "tool": _string(),
            "path": _string(),
            "result": REPO_STATUS_SCHEMA["schema"],
        },
        required=["version", "tool", "path", "result"],
    ),
)


MCP_CHECK_RESPONSE_SCHEMA = _named(
    "mcp-check-response",
    1,
    _object(
        properties={
            "version": _integer(),
            "tool": _string(),
            "path": _string(),
            "result": AGGREGATED_CHECK_SCHEMA["schema"],
        },
        required=["version", "tool", "path", "result"],
    ),
)


MCP_DETECT_RESPONSE_SCHEMA = _named(
    "mcp-detect-response",
    1,
    _object(
        properties={
            "version": _integer(),
            "tool": _string(),
            "path": _string(),
            "result": DETECT_RESULT_SCHEMA["schema"],
        },
        required=["version", "tool", "path", "result"],
    ),
)


MCP_UNDERSTAND_RESPONSE_SCHEMA = _named(
    "mcp-understand-response",
    1,
    _object(
        properties={
            "version": _integer(),
            "tool": _string(),
            "path": _string(),
            "output_dir": _string(),
            "compact_budget_tokens": _integer(),
            "result": UNDERSTAND_PAYLOAD_SCHEMA["schema"],
        },
        required=[
            "version",
            "tool",
            "path",
            "output_dir",
            "compact_budget_tokens",
            "result",
        ],
    ),
)


MCP_INIT_RESPONSE_SCHEMA = _named(
    "mcp-init-response",
    1,
    _object(
        properties={
            "version": _integer(),
            "tool": _string(),
            "path": _string(),
            "config_path": _string(),
            "config_written": _boolean(),
            "status": _string(),
            "summary": _string(),
            "dry_run": _boolean(),
            "write_policy": WRITE_POLICY_SCHEMA["schema"],
            "llm": _object(
                properties={
                    "request": LLM_OPTIONS_SCHEMA["schema"],
                    "result": LLM_ENHANCEMENT_RESULT_SCHEMA["schema"],
                },
                required=["request", "result"],
                nullable=True,
            ),
            "results": _array(FILE_RESULT_SCHEMA["schema"]),
        },
        required=[
            "version",
            "tool",
            "path",
            "config_path",
            "config_written",
            "status",
            "summary",
            "dry_run",
            "write_policy",
            "llm",
            "results",
        ],
    ),
)


MCP_UPDATE_RESPONSE_SCHEMA = _named(
    "mcp-update-response",
    1,
    _object(
        properties={
            "version": _integer(),
            "tool": _string(),
            "path": _string(),
            "status": _string(),
            "summary": _string(),
            "dry_run": _boolean(),
            "write_policy": WRITE_POLICY_SCHEMA["schema"],
            "llm": _object(
                properties={
                    "request": LLM_OPTIONS_SCHEMA["schema"],
                    "result": LLM_ENHANCEMENT_RESULT_SCHEMA["schema"],
                },
                required=["request", "result"],
                nullable=True,
            ),
            "results": _array(FILE_RESULT_SCHEMA["schema"]),
        },
        required=[
            "version",
            "tool",
            "path",
            "status",
            "summary",
            "dry_run",
            "write_policy",
            "llm",
            "results",
        ],
    ),
)


MCP_PACK_RESPONSE_SCHEMA = _named(
    "mcp-pack-response",
    1,
    _object(
        properties={
            "version": _integer(),
            "tool": _string(),
            "path": _string(),
            "status": _string(),
            "summary": _string(),
            "dry_run": _boolean(),
            "check": _boolean(),
            "drift": _boolean(),
            "write_policy": WRITE_POLICY_SCHEMA["schema"],
            "results": _array(FILE_RESULT_SCHEMA["schema"]),
        },
        required=[
            "version",
            "tool",
            "path",
            "status",
            "summary",
            "dry_run",
            "check",
            "drift",
            "write_policy",
            "results",
        ],
    ),
)


SCHEMAS: dict[str, Schema] = {
    "analysis_payload": ANALYSIS_PAYLOAD_SCHEMA,
    "cli_analyze_response": CLI_ANALYZE_RESPONSE_SCHEMA,
    "cli_meta_response": CLI_META_RESPONSE_SCHEMA,
    "cli_pack_plan_response": CLI_PACK_PLAN_RESPONSE_SCHEMA,
    "cli_pack_response": CLI_PACK_RESPONSE_SCHEMA,
    "cli_task_response": CLI_TASK_RESPONSE_SCHEMA,
    "cli_understand_response": CLI_UNDERSTAND_RESPONSE_SCHEMA,
    "detect_result": DETECT_RESULT_SCHEMA,
    "entrypoints": ENTRYPOINTS_SCHEMA,
    "file_result": FILE_RESULT_SCHEMA,
    "knowledge": KNOWLEDGE_SCHEMA,
    "llm_enhancement_result": LLM_ENHANCEMENT_RESULT_SCHEMA,
    "llm_options": LLM_OPTIONS_SCHEMA,
    "write_policy": WRITE_POLICY_SCHEMA,
    "id_context": ID_CONTEXT_SCHEMA,
    "metadata_payload": METADATA_PAYLOAD_SCHEMA,
    "mcp_check_response": MCP_CHECK_RESPONSE_SCHEMA,
    "mcp_detect_response": MCP_DETECT_RESPONSE_SCHEMA,
    "mcp_init_response": MCP_INIT_RESPONSE_SCHEMA,
    "mcp_pack_response": MCP_PACK_RESPONSE_SCHEMA,
    "mcp_status_response": MCP_STATUS_RESPONSE_SCHEMA,
    "mcp_understand_response": MCP_UNDERSTAND_RESPONSE_SCHEMA,
    "mcp_update_response": MCP_UPDATE_RESPONSE_SCHEMA,
    "task_contract": TASK_CONTRACT_SCHEMA,
    "task_evidence": TASK_EVIDENCE_SCHEMA,
    "task_verdict": TASK_VERDICT_SCHEMA,
    "aggregated_check": AGGREGATED_CHECK_SCHEMA,
    "repo_status": REPO_STATUS_SCHEMA,
    "understand_payload": UNDERSTAND_PAYLOAD_SCHEMA,
}


def contract_schema(name: str) -> Schema:
    try:
        return SCHEMAS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown contract schema: {name}") from exc


def schema_snapshots() -> dict[str, Schema]:
    return {name: contract_schema(name) for name in sorted(SCHEMAS)}


def _validate_scalar(name: str, expected: str, value: object) -> None:
    if expected == "string" and not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if expected == "integer" and not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if expected == "boolean" and not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")


def _validate_schema(name: str, schema: Schema, value: object) -> None:
    if value is None:
        if bool(schema.get("nullable", False)):
            return
        raise ValueError(f"{name} may not be null")
    schema_type = str(schema.get("type", ""))
    if schema_type in {"string", "integer", "boolean"}:
        _validate_scalar(name, schema_type, value)
        enum = schema.get("enum")
        if enum is not None and value not in enum:
            raise ValueError(f"{name} must be one of: {', '.join(str(item) for item in enum)}")
        return
    if schema_type == "array":
        if not isinstance(value, list):
            raise ValueError(f"{name} must be an array")
        item_schema = dict(schema.get("items", {}))
        for index, item in enumerate(value):
            _validate_schema(f"{name}[{index}]", item_schema, item)
        return
    if schema_type == "object":
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be an object")
        required = [str(item) for item in schema.get("required", [])]
        properties = dict(schema.get("properties", {}))
        for key in required:
            if key not in value:
                raise ValueError(f"{name}.{key} is required")
        for key, item_schema in properties.items():
            if key in value:
                _validate_schema(f"{name}.{key}", dict(item_schema), value[key])
        if not bool(schema.get("additional_properties", True)):
            unknown = sorted(set(value.keys()) - set(properties.keys()))
            if unknown:
                raise ValueError(f"{name} has unknown properties: {', '.join(unknown)}")
        return
    raise ValueError(f"{name} has unsupported schema type: {schema_type}")


def validate_contract_payload(name: str, payload: dict[str, Any]) -> None:
    schema = contract_schema(name)
    _validate_schema(name, dict(schema["schema"]), payload)
