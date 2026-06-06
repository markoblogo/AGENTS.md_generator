from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

import agentsgen.cli_extra as cli_extra_module
from agentsgen.cli import app
from agentsgen.result_types import FileResult
from agentsgen.validators import (
    validate_aggregated_check_payload,
    validate_cli_analyze_response_payload,
    validate_cli_meta_response_payload,
    validate_cli_pack_plan_response_payload,
    validate_cli_pack_response_payload,
    validate_cli_task_response_payload,
    validate_cli_understand_response_payload,
    validate_detect_result_payload,
    validate_repo_status_payload,
)


FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def _copy_fixture(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)


def test_cli_detect_json_matches_contract(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)

    result = runner.invoke(app, ["detect", str(target), "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    validate_detect_result_payload(payload)


def test_cli_status_and_check_json_match_contracts(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)

    assert runner.invoke(
        app, ["init", str(target), "--defaults", "--autodetect", "--name", "repo"]
    ).exit_code == 0
    assert runner.invoke(app, ["pack", str(target), "--autodetect"]).exit_code == 0

    status_result = runner.invoke(app, ["status", str(target), "--format", "json"])
    assert status_result.exit_code in {0, 1, 2}
    validate_repo_status_payload(json.loads(status_result.stdout))

    check_result = runner.invoke(
        app, ["check", str(target), "--format", "json", "--pack-check"]
    )
    assert check_result.exit_code in {0, 1, 2}
    validate_aggregated_check_payload(json.loads(check_result.stdout))


def test_cli_pack_json_contracts(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)

    response = runner.invoke(
        app, ["pack", str(target), "--dry-run", "--format", "json", "--files", "llms"]
    )
    assert response.exit_code == 0
    validate_cli_pack_response_payload(json.loads(response.stdout))

    plan = runner.invoke(
        app,
        ["pack", str(target), "--autodetect", "--print-plan", "--format", "json"],
    )
    assert plan.exit_code == 0
    validate_cli_pack_plan_response_payload(json.loads(plan.stdout))


def test_cli_understand_and_task_json_contracts(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)

    assert runner.invoke(
        app, ["init", str(target), "--defaults", "--autodetect", "--name", "repo"]
    ).exit_code == 0

    understand = runner.invoke(app, ["understand", str(target), "--format", "json"])
    assert understand.exit_code == 0
    validate_cli_understand_response_payload(json.loads(understand.stdout))

    task_init = runner.invoke(
        app, ["task", "init", "demo-task", str(target), "--format", "json"]
    )
    assert task_init.exit_code == 0
    validate_cli_task_response_payload(json.loads(task_init.stdout))

    task_evidence = runner.invoke(
        app,
        [
            "task",
            "evidence",
            "demo-task",
            str(target),
            "--check",
            "pytest=passed",
            "--artifact",
            "AGENTS.md",
            "--format",
            "json",
        ],
    )
    assert task_evidence.exit_code == 0
    validate_cli_task_response_payload(json.loads(task_evidence.stdout))

    task_verdict = runner.invoke(
        app,
        [
            "task",
            "verdict",
            "demo-task",
            str(target),
            "--status",
            "pass",
            "--format",
            "json",
        ],
    )
    assert task_verdict.exit_code == 0
    validate_cli_task_response_payload(json.loads(task_verdict.stdout))


def test_cli_analyze_and_meta_json_contracts(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)

    def _analysis_stub(*args, **kwargs):
        payload = {
            "version": 1,
            "generated_by": "agentsgen",
            "generated_at": "",
            "url": "https://example.com",
            "final_url": "https://example.com",
            "mode": "heuristic",
            "score": 42,
            "visibility": "medium",
            "summary": "demo",
            "factors": {},
            "evidence": {},
            "recommendations": [],
        }
        return ([FileResult(path=Path("docs/ai/llmo-score.json"), action="created")], payload)

    def _meta_stub(*args, **kwargs):
        payload = {
            "version": 1,
            "generated_by": "agentsgen",
            "generated_at": "",
            "url": "https://example.com",
            "final_url": "https://example.com",
            "mode": "ai",
            "result": {
                "title": "Example",
                "description": "Desc",
                "keywords": ["one"],
                "shortDescription": "Short",
            },
        }
        return ([FileResult(path=Path("docs/ai/llmo-meta.json"), action="created")], payload)

    monkeypatch.setattr(cli_extra_module, "apply_analysis", _analysis_stub)
    monkeypatch.setattr(cli_extra_module, "apply_metadata", _meta_stub)

    analyze = runner.invoke(
        app, ["analyze", "example.com", str(target), "--format", "json"]
    )
    assert analyze.exit_code == 0
    validate_cli_analyze_response_payload(json.loads(analyze.stdout))

    meta = runner.invoke(
        app, ["meta", "example.com", str(target), "--format", "json"]
    )
    assert meta.exit_code == 0
    validate_cli_meta_response_payload(json.loads(meta.stdout))
