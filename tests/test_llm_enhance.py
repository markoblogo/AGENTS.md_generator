from __future__ import annotations

import os
from pathlib import Path

from typer.testing import CliRunner

from agentsgen.cli import app
import agentsgen.llm as llm_module
from agentsgen.llm import (
    LLMEnhancementRequest,
    LLMEnhancementResult,
    LLMEnhancer,
    enhance_sections,
)


runner = CliRunner()


class _StubEnhancer(LLMEnhancer):
    def __init__(
        self, result: LLMEnhancementResult | None = None, exc: Exception | None = None
    ):
        self._result = result
        self._exc = exc

    def enhance(self, request: LLMEnhancementRequest) -> LLMEnhancementResult:
        if self._exc is not None:
            raise self._exc
        assert self._result is not None
        return self._result


def test_openai_enhancement_falls_back_without_credentials(tmp_path: Path) -> None:
    old = os.environ.pop("OPENAI_API_KEY", None)
    try:
        result = enhance_sections(
            LLMEnhancementRequest(target=tmp_path, provider="openai")
        )
    finally:
        if old is not None:
            os.environ["OPENAI_API_KEY"] = old
    assert result.applied is False
    assert "falling back" in result.message.lower()


def test_init_accepts_llm_flags_without_provider_failure(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            str(tmp_path),
            "--defaults",
            "--stack",
            "static",
            "--name",
            "demo",
            "--llm-enhance",
            "--llm-provider",
            "openai",
        ],
    )
    assert result.exit_code == 0


def test_enhancement_timeout_falls_back(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setitem(
        llm_module.PROVIDER_FACTORIES,
        "openai",
        lambda: _StubEnhancer(exc=TimeoutError()),
    )
    result = enhance_sections(LLMEnhancementRequest(target=tmp_path, provider="openai"))
    assert result.applied is False
    assert "timed out" in result.message.lower()
    assert "falling back" in result.message.lower()


def test_enhancement_provider_error_falls_back(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setitem(
        llm_module.PROVIDER_FACTORIES,
        "openai",
        lambda: _StubEnhancer(exc=RuntimeError("boom")),
    )
    result = enhance_sections(LLMEnhancementRequest(target=tmp_path, provider="openai"))
    assert result.applied is False
    assert "failed" in result.message.lower()
    assert "boom" in result.message


def test_init_with_llm_enhance_injects_mocked_repo_context(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setitem(
        llm_module.PROVIDER_FACTORIES,
        "openai",
        lambda: _StubEnhancer(
            result=LLMEnhancementResult(
                provider="openai",
                applied=True,
                sections={"repo_context": "Injected LLM repo context"},
                message="ok",
            )
        ),
    )
    result = runner.invoke(
        app,
        [
            "init",
            str(tmp_path),
            "--defaults",
            "--stack",
            "static",
            "--name",
            "demo",
            "--llm-enhance",
            "--llm-provider",
            "openai",
        ],
    )
    assert result.exit_code == 0
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "Injected LLM repo context" in agents


def test_init_without_llm_enhance_does_not_call_provider(
    monkeypatch, tmp_path: Path
) -> None:
    calls = {"count": 0}

    def _factory() -> LLMEnhancer:
        calls["count"] += 1
        return _StubEnhancer(
            result=LLMEnhancementResult(
                provider="openai",
                applied=True,
                sections={"repo_context": "should not appear"},
                message="ok",
            )
        )

    monkeypatch.setitem(llm_module.PROVIDER_FACTORIES, "openai", _factory)
    result = runner.invoke(
        app,
        [
            "init",
            str(tmp_path),
            "--defaults",
            "--stack",
            "static",
            "--name",
            "demo",
        ],
    )
    assert result.exit_code == 0
    assert calls["count"] == 0
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "should not appear" not in agents


def test_update_with_llm_timeout_keeps_local_generation(
    monkeypatch, tmp_path: Path
) -> None:
    init_result = runner.invoke(
        app,
        [
            "init",
            str(tmp_path),
            "--defaults",
            "--stack",
            "static",
            "--name",
            "demo",
        ],
    )
    assert init_result.exit_code == 0

    monkeypatch.setitem(
        llm_module.PROVIDER_FACTORIES,
        "openai",
        lambda: _StubEnhancer(exc=TimeoutError()),
    )
    update_result = runner.invoke(
        app,
        [
            "update",
            str(tmp_path),
            "--llm-enhance",
            "--llm-provider",
            "openai",
        ],
    )
    assert update_result.exit_code == 0
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "Injected LLM repo context" not in agents
