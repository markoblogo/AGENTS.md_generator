from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from agentsgen.cli import app


FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def _copy_fixture(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)


def test_understand_python_uv_writes_artifacts_and_schema(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)
    (target / "src" / "app" / "core.py").write_text(
        "from .utils import helper\n\n\ndef run():\n    return helper()\n",
        encoding="utf-8",
    )
    (target / "src" / "app" / "utils.py").write_text(
        "def helper():\n    return 'ok'\n",
        encoding="utf-8",
    )

    res = runner.invoke(app, ["understand", str(target), "--format", "json"])
    assert res.exit_code == 0

    payload = json.loads(res.stdout)
    assert payload["version"] == 1
    assert payload["command"] == "understand"
    assert payload["stack"] == "python"

    knowledge_path = target / "agents.knowledge.json"
    repomap_path = target / "docs" / "ai" / "repomap.md"
    graph_path = target / "docs" / "ai" / "graph.mmd"
    assert knowledge_path.is_file()
    assert repomap_path.is_file()
    assert graph_path.is_file()

    knowledge = json.loads(knowledge_path.read_text(encoding="utf-8"))
    assert knowledge["version"] == 1
    assert knowledge["repo_path"] == "."
    assert isinstance(knowledge["files"], list) and knowledge["files"]
    assert any(row["path"].endswith("src/app/core.py") for row in knowledge["files"])
    assert any(edge["kind"] == "import" for edge in knowledge["edges"])


def test_understand_node_only_writes_expected_artifacts(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "node_pnpm", target)
    (target / "server.js").write_text(
        "const { helper } = require('./lib/helper');\nfunction main(){ return helper(); }\nmodule.exports = { main };\n",
        encoding="utf-8",
    )
    (target / "lib").mkdir()
    (target / "lib" / "helper.js").write_text(
        "function helper(){ return 'ok'; }\nmodule.exports = { helper };\n",
        encoding="utf-8",
    )
    before = {
        str(path.relative_to(target)).replace("\\", "/")
        for path in target.rglob("*")
        if path.is_file()
    }

    res = runner.invoke(app, ["understand", str(target), "--format", "json"])
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["stack"] == "node"

    after = {
        str(path.relative_to(target)).replace("\\", "/")
        for path in target.rglob("*")
        if path.is_file()
    }
    assert after - before == {
        "agents.knowledge.json",
        "docs/ai/repomap.md",
        "docs/ai/graph.mmd",
    }

    knowledge = json.loads((target / "agents.knowledge.json").read_text(encoding="utf-8"))
    assert any(item["label"] == "dev" for item in knowledge["entrypoints"])
    assert any(item["source"] == "package.json" for item in knowledge["entrypoints"])


def test_understand_mixed_monorepo_emits_compact_outputs(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "monorepo_mixed", target)
    (target / "apps" / "web" / "index.ts").write_text(
        "import { thing } from './shared';\nexport function boot(){ return thing; }\n",
        encoding="utf-8",
    )
    (target / "apps" / "web" / "shared.ts").write_text(
        "export const thing = 'ok';\n",
        encoding="utf-8",
    )
    (target / "services" / "api" / "src").mkdir()
    (target / "services" / "api" / "src" / "__init__.py").write_text(
        "from .core import handler\n",
        encoding="utf-8",
    )
    (target / "services" / "api" / "src" / "core.py").write_text(
        "def handler():\n    return 'ok'\n",
        encoding="utf-8",
    )

    res = runner.invoke(app, ["understand", str(target), "--format", "json"])
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["stack"] == "mixed"

    graph = (target / "docs" / "ai" / "graph.mmd").read_text(encoding="utf-8")
    assert "graph TD" in graph
    assert "apps/web/index.ts" in graph or "services/api/src/core.py" in graph

    knowledge = json.loads((target / "agents.knowledge.json").read_text(encoding="utf-8"))
    assert knowledge["version"] == 1
    assert len(knowledge["edges"]) <= 30
