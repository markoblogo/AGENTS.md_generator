from __future__ import annotations

import pytest

from agentsgen.contracts import schema_snapshots
from agentsgen.validators import (
    validate_analysis_payload,
    validate_aggregated_check_payload,
    validate_cli_analyze_response_payload,
    validate_cli_meta_response_payload,
    validate_cli_pack_plan_response_payload,
    validate_cli_pack_response_payload,
    validate_cli_reflect_sessions_response_payload,
    validate_cli_reflect_skills_response_payload,
    validate_cli_task_response_payload,
    validate_cli_understand_response_payload,
    validate_detect_result_payload,
    validate_entrypoints_payload,
    validate_id_context_payload,
    validate_knowledge_payload,
    validate_llm_enhancement_result_payload,
    validate_llm_options_payload,
    validate_mcp_check_response_payload,
    validate_mcp_detect_response_payload,
    validate_mcp_init_response_payload,
    validate_mcp_pack_response_payload,
    validate_mcp_status_response_payload,
    validate_mcp_understand_response_payload,
    validate_mcp_update_response_payload,
    validate_metadata_payload,
    validate_reflect_sessions_payload,
    validate_reflect_signals_payload,
    validate_reflect_skill_usage_payload,
    validate_repo_status_payload,
    validate_task_contract_payload,
    validate_task_evidence_payload,
    validate_task_verdict_payload,
    validate_tool_config_payload,
    validate_understand_payload,
    validate_write_policy_payload,
)


def test_validate_tool_config_payload_accepts_v1_shape() -> None:
    validate_tool_config_payload(
        {
            "version": 1,
            "mode": "safe",
            "on_missing_markers": "write_generated",
            "generated_suffix": ".generated",
            "markers": {"start": "a", "end": "b"},
            "sections": [],
            "presets": {},
            "defaults": {},
            "project": {},
            "paths": {},
            "commands": {},
            "evidence": {},
            "pack": {
                "enabled": True,
                "llms_format": "txt",
                "output_dir": "docs/ai",
                "files": [],
            },
        }
    )


def test_validate_tool_config_payload_rejects_bad_pack_shape() -> None:
    with pytest.raises(ValueError):
        validate_tool_config_payload({"version": 1, "markers": {}, "pack": []})


def test_validate_other_payloads_accept_minimal_shapes() -> None:
    validate_repo_status_payload(
        {
            "status": "ok",
            "path": ".",
            "config": {"present": True},
            "agents_md": {
                "present": True,
                "markers": True,
                "marker_sections": 1,
                "generated_sibling": False,
            },
            "runbook_md": {
                "present": True,
                "markers": True,
                "marker_sections": 1,
                "generated_sibling": False,
            },
            "pack": {"status": "ok", "findings": [], "errors": []},
            "generated": {"count": 0, "files": []},
            "summary": {"drift": 0, "errors": 0},
        }
    )
    validate_aggregated_check_payload(
        {
            "version": 1,
            "command": "check",
            "path": ".",
            "status": "ok",
            "checks": {
                "core": {
                    "status": "ok",
                    "drift_count": 0,
                    "error_count": 0,
                    "warnings_count": 0,
                    "results": [],
                    "raw": {"exit_code": 0, "problems": [], "warnings": []},
                },
                "pack": None,
                "snippets": None,
            },
            "summary": {
                "ok": True,
                "drift_count": 0,
                "error_count": 0,
                "skipped_count": 0,
            },
        }
    )
    validate_entrypoints_payload(
        {
            "version": 1,
            "generated_by": "agentsgen",
            "generated_at": "",
            "repo": {"path": ".", "stack": "python", "autodetect": True},
            "commands": [
                {
                    "id": "test",
                    "title": "Test",
                    "command": "pytest -q",
                    "cwd": ".",
                    "source": {"kind": "config", "hint": ".agentsgen.json"},
                    "notes": "",
                }
            ],
        }
    )
    validate_knowledge_payload(
        {
            "version": 1,
            "repo_path": ".",
            "generated_at": "",
            "files": [],
            "edges": [],
            "entrypoints": [],
            "changed_files": [],
            "entrypoint_files": [],
            "slice": {
                "focus_matches": [],
                "changed_only": False,
                "changed_matches": [],
            },
            "relevance": [],
        }
    )
    validate_id_context_payload(
        {
            "version": 1,
            "generated_by": "agentsgen",
            "generated_at": "",
            "repo": {
                "name": "repo",
                "path": ".",
                "stack": "python",
                "autodetect": True,
            },
            "handoff": {
                "consumer": "ID",
                "target": "agentsmd",
                "status": "ready",
                "purpose": "handoff",
            },
            "bundle": {
                "repo_docs": {"agents_md": "AGENTS.md", "runbook_md": "RUNBOOK.md"},
                "pack": {
                    "llms": "llms.txt",
                    "entrypoints": "agents.entrypoints.json",
                    "id_context": "docs/ai/id-context.json",
                    "how_to_run": "docs/ai/how-to-run.md",
                    "how_to_test": "docs/ai/how-to-test.md",
                    "architecture": "docs/ai/architecture.md",
                    "data_contracts": "docs/ai/data-contracts.md",
                    "security": "SECURITY_AI.md",
                    "contributing": "CONTRIBUTING_AI.md",
                    "readme_snippets": "README_SNIPPETS.md",
                },
                "optional_repo_artifacts": {
                    "repomap": "docs/ai/repomap.md",
                    "repomap_compact": "docs/ai/repomap.compact.md",
                    "graph": "docs/ai/graph.mmd",
                    "knowledge": "agents.knowledge.json",
                    "proof_tasks_dir": "docs/ai/tasks",
                },
            },
            "usage": {
                "preferred_inputs": [],
                "preferred_human_bootstrap": [
                    "profiles/<owner>/soul.md",
                    "profiles/<owner>/profile.core.md",
                    "profiles/<owner>/handshake.md",
                ],
                "notes": [],
            },
        }
    )
    validate_task_contract_payload(
        {
            "version": 1,
            "generated_by": "agentsgen",
            "generated_at": "",
            "task_id": "demo",
            "title": "Demo",
            "summary": "demo",
            "acceptance": [],
            "path": "docs/ai/tasks/demo/contract.md",
        }
    )
    validate_task_evidence_payload(
        {
            "version": 2,
            "generated_by": "agentsgen",
            "generated_at": "",
            "task_id": "demo",
            "checks": [],
            "check_summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "pending": 0,
                "recorded": 0,
            },
            "changed_files": [],
            "changed_files_count": 0,
            "artifacts": [],
            "artifact_details": [],
            "artifact_summary": {"total": 0, "present": 0, "missing": 0},
            "contract_present": True,
            "evidence_status": "complete",
            "repo_state": {"git_available": False, "working_tree_dirty": False},
            "notes": [],
        }
    )
    validate_task_verdict_payload(
        {
            "version": 2,
            "generated_by": "agentsgen",
            "generated_at": "",
            "task_id": "demo",
            "status": "pass",
            "summary": "ok",
            "blocking_items": [],
            "blocking_details": [],
            "evidence_status": "complete",
            "check_summary": {},
            "artifact_summary": {},
            "review_ready": False,
            "ready_for_apply": True,
            "decision": "approved",
            "recommendation": "ship it",
        }
    )
    validate_detect_result_payload(
        {
            "project": {},
            "paths": {},
            "commands": {},
            "evidence": {"python": [], "node": [], "make": [], "ci": []},
            "rationale": [],
        }
    )
    validate_understand_payload(
        {
            "stack": "python",
            "repomap": "",
            "compact_repomap": "",
            "graph": "",
            "knowledge": {
                "version": 1,
                "repo_path": ".",
                "generated_at": "",
                "files": [],
                "edges": [],
                "entrypoints": [],
                "changed_files": [],
                "entrypoint_files": [],
                "slice": {
                    "focus": None,
                    "focus_matches": [],
                    "changed_only": False,
                    "changed_matches": [],
                },
                "relevance": [],
            },
            "summary": {
                "files_count": 0,
                "edges_count": 0,
                "entrypoints_count": 0,
                "changed_files_count": 0,
                "compact_budget_tokens": 4000,
                "focus": None,
                "changed_only": False,
                "slice_files_count": 0,
            },
        }
    )
    validate_analysis_payload(
        {
            "version": 1,
            "generated_by": "agentsgen",
            "generated_at": "",
            "url": "https://example.com",
            "final_url": "https://example.com",
            "mode": "heuristic",
            "score": 0,
            "visibility": "low",
            "summary": "demo",
            "factors": {},
            "evidence": {},
            "recommendations": [],
        }
    )
    validate_metadata_payload(
        {
            "version": 1,
            "generated_by": "agentsgen",
            "generated_at": "",
            "url": "https://example.com",
            "final_url": "https://example.com",
            "mode": "ai",
            "result": {
                "title": "",
                "description": "",
                "keywords": [],
                "shortDescription": "",
            },
        }
    )
    validate_cli_understand_response_payload(
        {
            "version": 1,
            "command": "understand",
            "path": ".",
            "output_dir": "docs/ai",
            "stack": "python",
            "summary": {
                "files_count": 0,
                "edges_count": 0,
                "entrypoints_count": 0,
                "changed_files_count": 0,
                "compact_budget_tokens": 4000,
                "focus": None,
                "changed_only": False,
                "slice_files_count": 0,
            },
            "changed_files": [],
            "slice": {
                "focus": None,
                "focus_matches": [],
                "changed_only": False,
                "changed_matches": [],
            },
            "relevance": [],
            "results": [],
        }
    )
    validate_cli_analyze_response_payload(
        {
            "version": 1,
            "command": "analyze",
            "path": ".",
            "output": "docs/ai/llmo-score.json",
            "result": {
                "version": 1,
                "generated_by": "agentsgen",
                "generated_at": "",
                "url": "https://example.com",
                "final_url": "https://example.com",
                "mode": "heuristic",
                "score": 0,
                "visibility": "low",
                "summary": "demo",
                "factors": {},
                "evidence": {},
                "recommendations": [],
            },
            "results": [],
        }
    )
    validate_cli_meta_response_payload(
        {
            "version": 1,
            "command": "meta",
            "path": ".",
            "output": "docs/ai/llmo-meta.json",
            "result": {
                "version": 1,
                "generated_by": "agentsgen",
                "generated_at": "",
                "url": "https://example.com",
                "final_url": "https://example.com",
                "mode": "ai",
                "result": {
                    "title": "",
                    "description": "",
                    "keywords": [],
                    "shortDescription": "",
                },
            },
            "results": [],
        }
    )
    validate_cli_task_response_payload(
        {
            "version": 1,
            "command": "task init",
            "path": ".",
            "output": "docs/ai/tasks/demo/contract.md",
            "result": {},
            "results": [],
        }
    )
    validate_cli_pack_response_payload(
        {
            "status": "ok",
            "summary": "pack:ok",
            "check": False,
            "dry_run": True,
            "results": [],
        }
    )
    validate_cli_pack_plan_response_payload(
        {
            "version": 1,
            "status": "ok",
            "summary": "pack:ok",
            "check": False,
            "dry_run": True,
            "print_plan": True,
            "plan": [],
        }
    )
    validate_reflect_sessions_payload(
        {
            "version": 1,
            "generated_by": "agentsgen",
            "generated_at": "",
            "repo": {"path": "."},
            "source": {"tool": "codex", "root": "/tmp/codex"},
            "sessions": [],
            "summary": {
                "session_count": 0,
                "prompt_count": 0,
                "prompt_chars_total": 0,
                "avg_prompt_chars": 0,
                "plan_first_sessions": 0,
                "redirect_count": 0,
                "long_sessions": 0,
            },
        }
    )
    validate_reflect_signals_payload(
        {
            "version": 1,
            "generated_by": "agentsgen",
            "generated_at": "",
            "repo": {"path": "."},
            "source": {"tool": "codex", "root": "/tmp/codex"},
            "summary": {
                "session_count": 0,
                "prompt_count": 0,
                "avg_prompt_chars": 0,
                "plan_first_ratio": 0,
                "redirect_count": 0,
                "long_sessions": 0,
                "top_hours": [],
            },
            "top_short_prompts": [],
        }
    )
    validate_cli_reflect_sessions_response_payload(
        {
            "version": 1,
            "command": "reflect sessions",
            "path": ".",
            "output_dir": "docs/ai",
            "source": {"tool": "codex", "root": "/tmp/codex"},
            "summary": {
                "session_count": 0,
                "prompt_count": 0,
                "avg_prompt_chars": 0,
                "plan_first_ratio": 0,
                "redirect_count": 0,
                "long_sessions": 0,
                "top_hours": [],
            },
            "outputs": {
                "sessions_json": "docs/ai/agent-sessions.json",
                "signals_json": "docs/ai/agent-signals.json",
                "patterns_md": "docs/ai/agent-patterns.md",
            },
            "results": [],
        }
    )
    validate_reflect_skill_usage_payload(
        {
            "version": 1,
            "generated_by": "agentsgen",
            "generated_at": "",
            "repo": {"path": "."},
            "source": {"tool": "codex", "root": "/tmp/codex"},
            "summary": {
                "session_count": 0,
                "sessions_with_skills": 0,
                "skill_activation_count": 0,
                "unique_skills": 0,
            },
            "skills": [],
        }
    )
    validate_cli_reflect_skills_response_payload(
        {
            "version": 1,
            "command": "reflect skills",
            "path": ".",
            "output_dir": "docs/ai",
            "source": {"tool": "codex", "root": "/tmp/codex"},
            "summary": {
                "session_count": 0,
                "sessions_with_skills": 0,
                "skill_activation_count": 0,
                "unique_skills": 0,
            },
            "outputs": {
                "skill_usage_json": "docs/ai/skill-usage.json",
                "skill_effectiveness_md": "docs/ai/skill-effectiveness.md",
            },
            "results": [],
        }
    )
    validate_llm_options_payload(
        {
            "enabled": True,
            "provider": "openai",
            "model": "gpt-test",
            "timeout_seconds": 30,
            "narrative_sections": ["repo_context"],
        }
    )
    validate_llm_enhancement_result_payload(
        {
            "provider": "openai",
            "applied": True,
            "sections": {"repo_context": "hello"},
            "message": "ok",
        }
    )
    validate_write_policy_payload(
        {
            "mode": "apply",
            "may_write": True,
            "writes_applied": True,
        }
    )
    validate_mcp_status_response_payload(
        {
            "version": 1,
            "tool": "status",
            "path": ".",
            "result": {
                "status": "ok",
                "path": ".",
                "config": {"present": True},
                "agents_md": {
                    "present": True,
                    "markers": True,
                    "marker_sections": 1,
                    "generated_sibling": False,
                },
                "runbook_md": {
                    "present": True,
                    "markers": True,
                    "marker_sections": 1,
                    "generated_sibling": False,
                },
                "pack": {"status": "ok", "findings": [], "errors": []},
                "generated": {"count": 0, "files": []},
                "summary": {"drift": 0, "errors": 0},
            },
        }
    )
    validate_mcp_init_response_payload(
        {
            "version": 1,
            "tool": "init",
            "path": ".",
            "config_path": "./.agentsgen.json",
            "config_written": True,
            "status": "ok",
            "summary": "init:ok",
            "dry_run": False,
            "write_policy": {
                "mode": "apply",
                "may_write": True,
                "writes_applied": True,
            },
            "llm": None,
            "results": [],
        }
    )
    validate_mcp_update_response_payload(
        {
            "version": 1,
            "tool": "update",
            "path": ".",
            "status": "ok",
            "summary": "update:ok",
            "dry_run": False,
            "write_policy": {
                "mode": "apply",
                "may_write": True,
                "writes_applied": True,
            },
            "llm": None,
            "results": [],
        }
    )
    validate_mcp_pack_response_payload(
        {
            "version": 1,
            "tool": "pack",
            "path": ".",
            "status": "ok",
            "summary": "pack:ok",
            "dry_run": False,
            "check": False,
            "drift": False,
            "write_policy": {
                "mode": "apply",
                "may_write": True,
                "writes_applied": True,
            },
            "results": [],
        }
    )
    validate_mcp_check_response_payload(
        {
            "version": 1,
            "tool": "check",
            "path": ".",
            "result": {
                "version": 1,
                "command": "check",
                "path": ".",
                "status": "ok",
                "checks": {
                    "core": {
                        "status": "ok",
                        "drift_count": 0,
                        "error_count": 0,
                        "warnings_count": 0,
                        "results": [],
                        "raw": {"exit_code": 0, "problems": [], "warnings": []},
                    },
                    "pack": None,
                    "snippets": None,
                },
                "summary": {
                    "ok": True,
                    "drift_count": 0,
                    "error_count": 0,
                    "skipped_count": 0,
                },
            },
        }
    )
    validate_mcp_detect_response_payload(
        {
            "version": 1,
            "tool": "detect",
            "path": ".",
            "result": {
                "project": {},
                "paths": {},
                "commands": {},
                "evidence": {"python": [], "node": [], "make": [], "ci": []},
                "rationale": [],
            },
        }
    )
    validate_mcp_understand_response_payload(
        {
            "version": 1,
            "tool": "understand",
            "path": ".",
            "output_dir": "docs/ai",
            "compact_budget_tokens": 4000,
            "result": {
                "stack": "python",
                "repomap": "",
                "compact_repomap": "",
                "graph": "",
                "knowledge": {
                    "version": 1,
                    "repo_path": ".",
                    "generated_at": "",
                    "files": [],
                    "edges": [],
                    "entrypoints": [],
                    "changed_files": [],
                    "entrypoint_files": [],
                    "slice": {
                        "focus": None,
                        "focus_matches": [],
                        "changed_only": False,
                        "changed_matches": [],
                    },
                    "relevance": [],
                },
                "summary": {
                    "files_count": 0,
                    "edges_count": 0,
                    "entrypoints_count": 0,
                    "changed_files_count": 0,
                    "compact_budget_tokens": 4000,
                    "focus": None,
                    "changed_only": False,
                    "slice_files_count": 0,
                },
            },
        }
    )


def test_schema_snapshots_catalog_contains_target_contracts() -> None:
    snapshots = schema_snapshots()
    assert sorted(snapshots) == [
        "aggregated_check",
        "analysis_payload",
        "cli_analyze_response",
        "cli_meta_response",
        "cli_pack_plan_response",
        "cli_pack_response",
        "cli_reflect_sessions_response",
        "cli_reflect_skills_response",
        "cli_task_response",
        "cli_understand_response",
        "detect_result",
        "entrypoints",
        "file_result",
        "id_context",
        "knowledge",
        "llm_enhancement_result",
        "llm_options",
        "mcp_check_response",
        "mcp_detect_response",
        "mcp_init_response",
        "mcp_pack_response",
        "mcp_status_response",
        "mcp_understand_response",
        "mcp_update_response",
        "metadata_payload",
        "reflect_sessions_payload",
        "reflect_signals_payload",
        "reflect_skill_usage_payload",
        "repo_status",
        "task_contract",
        "task_evidence",
        "task_verdict",
        "understand_payload",
        "write_policy",
    ]
