from __future__ import annotations

from typing import Any

from .contracts import validate_contract_payload


def _require_mapping(name: str, value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return dict(value)


def _require_string(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value


def _require_bool(name: str, value: object) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def _require_int(name: str, value: object) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _require_list(name: str, value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be an array")
    return list(value)


def validate_tool_config_payload(payload: dict[str, Any]) -> None:
    _require_int("version", payload.get("version", 1))
    for key in ["mode", "on_missing_markers", "generated_suffix"]:
        _require_string(key, payload.get(key, ""))
    markers = _require_mapping("markers", payload.get("markers", {}))
    for key in ["start", "end"]:
        _require_string(f"markers.{key}", markers.get(key, ""))
    _require_list("sections", payload.get("sections", []))
    for key in ["presets", "defaults", "project", "paths", "commands", "evidence"]:
        _require_mapping(key, payload.get(key, {}))
    pack = _require_mapping("pack", payload.get("pack", {}))
    _require_bool("pack.enabled", pack.get("enabled", True))
    _require_string("pack.llms_format", pack.get("llms_format", "txt"))
    _require_string("pack.output_dir", pack.get("output_dir", "docs/ai"))
    _require_list("pack.files", pack.get("files", []))


def validate_repo_status_payload(payload: dict[str, Any]) -> None:
    for key in ["status", "path"]:
        _require_string(key, payload.get(key, ""))
    _require_mapping("config", payload.get("config", {}))
    for key in ["agents_md", "runbook_md", "pack", "generated", "summary"]:
        _require_mapping(key, payload.get(key, {}))


def validate_aggregated_check_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("aggregated_check", payload)


def validate_entrypoints_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("entrypoints", payload)


def validate_knowledge_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("knowledge", payload)


def validate_id_context_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("id_context", payload)


def validate_task_contract_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("task_contract", payload)


def validate_task_evidence_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("task_evidence", payload)


def validate_task_verdict_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("task_verdict", payload)


def validate_detect_result_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("detect_result", payload)


def validate_understand_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("understand_payload", payload)


def validate_analysis_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("analysis_payload", payload)


def validate_metadata_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("metadata_payload", payload)


def validate_cli_understand_response_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("cli_understand_response", payload)


def validate_cli_analyze_response_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("cli_analyze_response", payload)


def validate_cli_meta_response_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("cli_meta_response", payload)


def validate_cli_task_response_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("cli_task_response", payload)


def validate_cli_pack_response_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("cli_pack_response", payload)


def validate_cli_reflect_sessions_response_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("cli_reflect_sessions_response", payload)


def validate_cli_reflect_skills_response_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("cli_reflect_skills_response", payload)


def validate_cli_pack_plan_response_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("cli_pack_plan_response", payload)


def validate_llm_options_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("llm_options", payload)


def validate_llm_enhancement_result_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("llm_enhancement_result", payload)


def validate_write_policy_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("write_policy", payload)


def validate_mcp_status_response_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("mcp_status_response", payload)


def validate_mcp_check_response_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("mcp_check_response", payload)


def validate_mcp_detect_response_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("mcp_detect_response", payload)


def validate_mcp_understand_response_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("mcp_understand_response", payload)


def validate_mcp_init_response_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("mcp_init_response", payload)


def validate_mcp_update_response_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("mcp_update_response", payload)


def validate_mcp_pack_response_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("mcp_pack_response", payload)


def validate_reflect_sessions_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("reflect_sessions_payload", payload)


def validate_reflect_signals_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("reflect_signals_payload", payload)


def validate_reflect_skill_usage_payload(payload: dict[str, Any]) -> None:
    validate_contract_payload("reflect_skill_usage_payload", payload)
