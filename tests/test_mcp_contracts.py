from __future__ import annotations

import shutil
import sys
import types
from pathlib import Path

import agentsgen.llm as llm_module
from agentsgen.llm import LLMEnhancementResult, LLMEnhancer, LLMEnhancementRequest
from agentsgen.mcp_server import (
    build_mcp_check_response,
    build_mcp_detect_response,
    build_mcp_init_response,
    build_mcp_pack_response,
    build_mcp_status_response,
    build_mcp_understand_response,
    build_mcp_update_response,
)
from agentsgen.validators import (
    validate_mcp_check_response_payload,
    validate_mcp_detect_response_payload,
    validate_mcp_init_response_payload,
    validate_mcp_pack_response_payload,
    validate_mcp_status_response_payload,
    validate_mcp_understand_response_payload,
    validate_mcp_update_response_payload,
)


FIXTURES = Path(__file__).parent / "fixtures"


class _StubEnhancer(LLMEnhancer):
    def enhance(self, request: LLMEnhancementRequest) -> LLMEnhancementResult:
        return LLMEnhancementResult(
            provider=request.provider,
            applied=True,
            sections={"repo_context": "Injected MCP LLM repo context"},
            message="ok",
        )


def _copy_fixture(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)


def test_mcp_read_only_contracts_match_end_to_end_payloads(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)

    status_payload = build_mcp_status_response(str(target))
    validate_mcp_status_response_payload(status_payload)
    assert status_payload["tool"] == "status"
    assert status_payload["path"] == str(target)

    check_payload = build_mcp_check_response(str(target))
    validate_mcp_check_response_payload(check_payload)
    assert check_payload["tool"] == "check"
    assert check_payload["result"]["command"] == "check"

    detect_payload = build_mcp_detect_response(str(target))
    validate_mcp_detect_response_payload(detect_payload)
    assert detect_payload["tool"] == "detect"
    assert "project" in detect_payload["result"]

    understand_payload = build_mcp_understand_response(
        str(target),
        compact_budget_tokens=1024,
    )
    validate_mcp_understand_response_payload(understand_payload)
    assert understand_payload["tool"] == "understand"
    assert understand_payload["compact_budget_tokens"] == 1024
    assert understand_payload["output_dir"] == str(target / "docs" / "ai")
    assert understand_payload["result"]["summary"]["compact_budget_tokens"] == 1024


def test_mcp_write_contracts_match_end_to_end_payloads(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)
    monkeypatch.setitem(
        llm_module.PROVIDER_FACTORIES,
        "openai",
        lambda: _StubEnhancer(),
    )

    init_payload = build_mcp_init_response(
        str(target),
        stack="python",
        name="repo",
        dry_run=False,
        llm_enabled=True,
        llm_provider="openai",
        llm_model="gpt-test",
    )
    validate_mcp_init_response_payload(init_payload)
    assert init_payload["tool"] == "init"
    assert init_payload["config_written"] is True
    assert init_payload["write_policy"]["mode"] == "apply"
    assert init_payload["write_policy"]["writes_applied"] is True
    assert init_payload["llm"]["request"]["provider"] == "openai"
    assert init_payload["llm"]["result"]["applied"] is True

    update_payload = build_mcp_update_response(
        str(target),
        dry_run=True,
        llm_enabled=True,
        llm_provider="openai",
    )
    validate_mcp_update_response_payload(update_payload)
    assert update_payload["tool"] == "update"
    assert update_payload["dry_run"] is True
    assert update_payload["write_policy"]["mode"] == "dry-run"
    assert update_payload["write_policy"]["writes_applied"] is False
    assert update_payload["llm"]["result"]["provider"] == "openai"

    pack_payload = build_mcp_pack_response(
        str(target),
        autodetect=True,
        dry_run=True,
    )
    validate_mcp_pack_response_payload(pack_payload)
    assert pack_payload["tool"] == "pack"
    assert pack_payload["write_policy"]["mode"] == "dry-run"
    assert isinstance(pack_payload["results"], list)

    pack_check_payload = build_mcp_pack_response(
        str(target),
        autodetect=True,
        check=True,
    )
    validate_mcp_pack_response_payload(pack_check_payload)
    assert pack_check_payload["write_policy"]["mode"] == "check"
    assert pack_check_payload["write_policy"]["may_write"] is False


def test_mcp_serve_stdio_registers_protocol_tools(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)

    class _FakeFastMCP:
        last_instance: "_FakeFastMCP | None" = None

        def __init__(self, name: str):
            self.name = name
            self.tools: dict[str, object] = {}
            self.ran = False
            _FakeFastMCP.last_instance = self

        def tool(self):
            def _decorator(fn):
                self.tools[fn.__name__] = fn
                return fn

            return _decorator

        def run(self) -> None:
            self.ran = True

    mcp_module = types.ModuleType("mcp")
    server_module = types.ModuleType("mcp.server")
    fastmcp_module = types.ModuleType("mcp.server.fastmcp")
    fastmcp_module.FastMCP = _FakeFastMCP
    monkeypatch.setitem(sys.modules, "mcp", mcp_module)
    monkeypatch.setitem(sys.modules, "mcp.server", server_module)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_module)

    from agentsgen.mcp_server import serve_stdio

    serve_stdio()

    server = _FakeFastMCP.last_instance
    assert server is not None
    assert server.ran is True
    assert set(server.tools) == {
        "status",
        "check",
        "detect",
        "understand",
        "init",
        "update",
        "pack",
    }

    status_payload = server.tools["status"](path=str(target))
    validate_mcp_status_response_payload(status_payload)
    assert status_payload["tool"] == "status"

    pack_payload = server.tools["pack"](path=str(target), check=True)
    validate_mcp_pack_response_payload(pack_payload)
    assert pack_payload["write_policy"]["mode"] == "check"
