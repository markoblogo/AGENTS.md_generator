from __future__ import annotations

import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from agentsgen.cli import app


runner = CliRunner()


def test_task_init_writes_contract_markdown(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()

    res = runner.invoke(
        app,
        [
            "task",
            "init",
            "proof-loop-v0",
            str(target),
            "--title",
            "Proof Loop V0",
            "--summary",
            "Capture proof artifacts for the task.",
            "--acceptance",
            "Contract exists.",
            "--acceptance",
            "Evidence exists.",
            "--format",
            "json",
        ],
    )
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["command"] == "task init"
    assert payload["result"]["task_id"] == "proof-loop-v0"
    contract_path = target / "docs" / "ai" / "tasks" / "proof-loop-v0" / "contract.md"
    assert contract_path.is_file()
    text = contract_path.read_text(encoding="utf-8")
    assert "<!-- AGENTSGEN:START section=task_contract -->" in text
    assert "## Acceptance Criteria" in text
    assert "Contract exists." in text


def test_task_evidence_writes_json_and_tracks_changed_files(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / "README.md").write_text("hello\n", encoding="utf-8")

    subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "tests@example.com"],
        cwd=target,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Tests"],
        cwd=target,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=target, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=target,
        check=True,
        capture_output=True,
    )
    (target / "README.md").write_text("changed\n", encoding="utf-8")
    artifact_path = target / "docs" / "ai" / "repomap.compact.md"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("compact\n", encoding="utf-8")

    res = runner.invoke(
        app,
        [
            "task",
            "evidence",
            "proof-loop-v0",
            str(target),
            "--check",
            "pytest=passed",
            "--artifact",
            "docs/ai/repomap.compact.md",
            "--note",
            "Fresh verify pending.",
            "--format",
            "json",
        ],
    )
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["command"] == "task evidence"
    evidence_path = target / "docs" / "ai" / "tasks" / "proof-loop-v0" / "evidence.json"
    assert evidence_path.is_file()
    written = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert written["checks"][0]["name"] == "pytest"
    assert written["checks"][0]["status"] == "passed"
    assert written["check_summary"]["passed"] == 1
    assert written["artifact_summary"]["present"] == 1
    assert written["evidence_status"] == "complete"
    assert "README.md" in written["changed_files"]
    assert written["artifacts"] == ["docs/ai/repomap.compact.md"]


def test_task_verdict_preserves_user_json_and_writes_generated_sibling(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    output_dir = target / "docs" / "ai" / "tasks" / "proof-loop-v0"
    output_dir.mkdir(parents=True)
    output_path = output_dir / "verdict.json"
    output_path.write_text('{"owner":"user"}\n', encoding="utf-8")

    res = runner.invoke(
        app,
        [
            "task",
            "verdict",
            "proof-loop-v0",
            str(target),
            "--status",
            "needs-review",
            "--summary",
            "Review evidence before pass.",
        ],
    )
    assert res.exit_code == 0
    assert json.loads(output_path.read_text(encoding="utf-8")) == {"owner": "user"}
    generated_path = output_dir / "verdict.generated.json"
    assert generated_path.is_file()
    generated = json.loads(generated_path.read_text(encoding="utf-8"))
    assert generated["generated_by"] == "agentsgen"
    assert generated["status"] == "needs-review"


def test_task_verdict_reads_evidence_summary(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    task_output = target / "docs" / "ai" / "tasks" / "proof-loop-v0"
    task_output.mkdir(parents=True)
    (task_output / "evidence.json").write_text(
        json.dumps(
            {
                "version": 2,
                "generated_by": "agentsgen",
                "generated_at": "2026-03-25T00:00:00Z",
                "task_id": "proof-loop-v0",
                "check_summary": {
                    "total": 2,
                    "passed": 2,
                    "failed": 0,
                    "pending": 0,
                    "recorded": 0,
                },
                "artifact_summary": {"total": 2, "present": 2, "missing": 0},
                "evidence_status": "complete",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    res = runner.invoke(
        app,
        [
            "task",
            "verdict",
            "proof-loop-v0",
            str(target),
            "--status",
            "needs-review",
            "--summary",
            "Manual review still pending.",
            "--format",
            "json",
        ],
    )
    assert res.exit_code == 0
    payload = json.loads(res.stdout)["result"]
    assert payload["evidence_status"] == "complete"
    assert payload["check_summary"]["passed"] == 2
    assert payload["decision"] == "review-ready"
    assert payload["ready_for_apply"] is False
    assert "Review the captured evidence bundle" in payload["recommendation"]


def test_task_verdict_parses_blocking_details(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    res = runner.invoke(
        app,
        [
            "task",
            "verdict",
            "proof-loop-v0",
            str(target),
            "--status",
            "needs-review",
            "--summary",
            "Blocked by missing generated artifacts.",
            "--blocking-item",
            "high: repomap artifact is missing",
            "--format",
            "json",
        ],
    )
    assert res.exit_code == 0
    payload = json.loads(res.stdout)["result"]
    assert payload["decision"] == "blocked"
    assert payload["blocking_details"][0]["severity"] == "high"
    assert payload["blocking_details"][0]["message"] == "repomap artifact is missing"
