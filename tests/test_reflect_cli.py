from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agentsgen.cli import app
from agentsgen.validators import (
    validate_cli_reflect_sessions_response_payload,
    validate_cli_reflect_skills_response_payload,
    validate_reflect_skill_usage_payload,
    validate_reflect_sessions_payload,
    validate_reflect_signals_payload,
)


runner = CliRunner()


def _write_session(
    path: Path,
    *,
    session_id: str,
    cwd: Path,
    started_at: str,
    events: list[tuple[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "timestamp": started_at,
            "type": "session_meta",
            "payload": {
                "id": session_id,
                "timestamp": started_at,
                "cwd": str(cwd),
                "originator": "Codex Desktop",
                "source": "vscode",
            },
        }
    ]
    for timestamp, message in events:
        rows.append(
            {
                "timestamp": timestamp,
                "type": "event_msg",
                "payload": {"type": "user_message", "message": message},
            }
        )
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_reflect_sessions_writes_artifacts_and_matches_contracts(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    codex_root = tmp_path / "codex"
    _write_session(
        codex_root / "2026/06/13/one.jsonl",
        session_id="s1",
        cwd=target,
        started_at="2026-06-13T10:00:00Z",
        events=[
            ("2026-06-13T10:01:00Z", "plan the change first"),
            ("2026-06-13T10:10:00Z", "use this approach instead"),
        ],
    )
    _write_session(
        codex_root / "2026/06/13/two.jsonl",
        session_id="s2",
        cwd=target / "src",
        started_at="2026-06-13T22:00:00Z",
        events=[
            ("2026-06-13T22:01:00Z", "fix tests"),
        ],
    )
    _write_session(
        codex_root / "2026/06/13/other.jsonl",
        session_id="s3",
        cwd=tmp_path / "other",
        started_at="2026-06-13T09:00:00Z",
        events=[
            ("2026-06-13T09:01:00Z", "ignore this repo"),
        ],
    )

    result = runner.invoke(
        app,
        [
            "reflect",
            "sessions",
            str(target),
            "--codex-root",
            str(codex_root),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    validate_cli_reflect_sessions_response_payload(payload)
    assert payload["summary"]["session_count"] == 2
    assert payload["summary"]["redirect_count"] == 1
    assert payload["summary"]["plan_first_ratio"] == 50

    sessions_json = target / "docs" / "ai" / "agent-sessions.json"
    signals_json = target / "docs" / "ai" / "agent-signals.json"
    patterns_md = target / "docs" / "ai" / "agent-patterns.md"
    assert sessions_json.is_file()
    assert signals_json.is_file()
    assert patterns_md.is_file()

    sessions_payload = json.loads(sessions_json.read_text(encoding="utf-8"))
    signals_payload = json.loads(signals_json.read_text(encoding="utf-8"))
    validate_reflect_sessions_payload(sessions_payload)
    validate_reflect_signals_payload(signals_payload)
    assert sessions_payload["summary"]["session_count"] == 2
    assert sessions_payload["sessions"][0]["session_id"] == "s1"
    assert "Most repeated short prompt" in patterns_md.read_text(encoding="utf-8")


def test_reflect_skills_writes_artifacts_and_matches_contracts(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    codex_root = tmp_path / "codex"
    _write_session(
        codex_root / "2026/06/13/one.jsonl",
        session_id="s1",
        cwd=target,
        started_at="2026-06-13T10:00:00Z",
        events=[
            ("2026-06-13T10:01:00Z", "use $session-retrospective"),
            ("2026-06-13T10:10:00Z", "use skill-effectiveness-audit skill instead"),
        ],
    )
    _write_session(
        codex_root / "2026/06/13/two.jsonl",
        session_id="s2",
        cwd=target,
        started_at="2026-06-13T22:00:00Z",
        events=[
            ("2026-06-13T22:01:00Z", "apply $session-retrospective"),
        ],
    )

    result = runner.invoke(
        app,
        [
            "reflect",
            "skills",
            str(target),
            "--codex-root",
            str(codex_root),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    validate_cli_reflect_skills_response_payload(payload)
    assert payload["summary"]["unique_skills"] == 2
    assert payload["summary"]["skill_activation_count"] == 3

    usage_json = target / "docs" / "ai" / "skill-usage.json"
    effectiveness_md = target / "docs" / "ai" / "skill-effectiveness.md"
    assert usage_json.is_file()
    assert effectiveness_md.is_file()

    usage_payload = json.loads(usage_json.read_text(encoding="utf-8"))
    validate_reflect_skill_usage_payload(usage_payload)
    assert usage_payload["summary"]["sessions_with_skills"] == 2
    assert usage_payload["skills"][0]["skill"] == "session-retrospective"
    assert "Skill Effectiveness Audit" in effectiveness_md.read_text(encoding="utf-8")
