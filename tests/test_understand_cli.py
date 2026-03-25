from __future__ import annotations

import json
import subprocess
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
    compact_path = target / "docs" / "ai" / "repomap.compact.md"
    graph_path = target / "docs" / "ai" / "graph.mmd"
    assert knowledge_path.is_file()
    assert repomap_path.is_file()
    assert compact_path.is_file()
    assert graph_path.is_file()

    knowledge = json.loads(knowledge_path.read_text(encoding="utf-8"))
    assert knowledge["version"] == 1
    assert knowledge["repo_path"] == "."
    assert isinstance(knowledge["files"], list) and knowledge["files"]
    assert any(row["path"].endswith("src/app/core.py") for row in knowledge["files"])
    assert any(edge["kind"] == "import" for edge in knowledge["edges"])
    assert "relevance" in knowledge and knowledge["relevance"]


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
        "docs/ai/repomap.compact.md",
        "docs/ai/graph.mmd",
    }

    knowledge = json.loads(
        (target / "agents.knowledge.json").read_text(encoding="utf-8")
    )
    assert any(item["label"] == "dev" for item in knowledge["entrypoints"])
    assert any(item["source"] == "package.json" for item in knowledge["entrypoints"])
    compact = (target / "docs" / "ai" / "repomap.compact.md").read_text(
        encoding="utf-8"
    )
    assert "Priority files" in compact


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

    knowledge = json.loads(
        (target / "agents.knowledge.json").read_text(encoding="utf-8")
    )
    assert knowledge["version"] == 1
    assert len(knowledge["edges"]) <= 30


def test_understand_prioritizes_git_changed_files_in_relevance(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)
    (target / "src" / "app").mkdir(parents=True, exist_ok=True)
    (target / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (target / "src" / "app" / "core.py").write_text(
        "from .utils import helper\n\n\ndef run():\n    return helper()\n",
        encoding="utf-8",
    )
    (target / "src" / "app" / "utils.py").write_text(
        "def helper():\n    return 'ok'\n",
        encoding="utf-8",
    )

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

    changed_file = target / "src" / "app" / "utils.py"
    changed_file.write_text(
        "def helper():\n    return 'changed'\n",
        encoding="utf-8",
    )

    res = runner.invoke(
        app,
        [
            "understand",
            str(target),
            "--format",
            "json",
            "--compact-budget",
            "512",
        ],
    )
    assert res.exit_code == 0

    payload = json.loads(res.stdout)
    assert "src/app/utils.py" in payload["changed_files"]
    assert payload["relevance"][0]["path"] == "src/app/utils.py"

    compact = (target / "docs" / "ai" / "repomap.compact.md").read_text(
        encoding="utf-8"
    )
    assert "git-changed" in compact


def test_understand_focus_limits_relevance_slice(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)
    (target / "src" / "app").mkdir(parents=True, exist_ok=True)
    (target / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (target / "src" / "app" / "core.py").write_text(
        "from .utils import helper\n\n\ndef run():\n    return helper()\n",
        encoding="utf-8",
    )
    (target / "src" / "app" / "utils.py").write_text(
        "def helper():\n    return 'ok'\n",
        encoding="utf-8",
    )

    res = runner.invoke(
        app,
        ["understand", str(target), "--format", "json", "--focus", "helper"],
    )
    assert res.exit_code == 0

    payload = json.loads(res.stdout)
    assert payload["slice"]["focus"] == "helper"
    assert payload["relevance"]
    assert payload["relevance"][0]["path"] in {"src/app/core.py", "src/app/utils.py"}
    compact = (target / "docs" / "ai" / "repomap.compact.md").read_text(
        encoding="utf-8"
    )
    assert "Focus: `helper`" in compact
    assert "focus:helper" in compact


def test_understand_changed_mode_limits_to_changed_neighborhood(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)
    (target / "src" / "app").mkdir(parents=True, exist_ok=True)
    (target / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (target / "src" / "app" / "core.py").write_text(
        "from .utils import helper\n\n\ndef run():\n    return helper()\n",
        encoding="utf-8",
    )
    (target / "src" / "app" / "utils.py").write_text(
        "def helper():\n    return 'ok'\n",
        encoding="utf-8",
    )
    (target / "src" / "app" / "other.py").write_text(
        "def noop():\n    return None\n",
        encoding="utf-8",
    )

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

    (target / "src" / "app" / "utils.py").write_text(
        "def helper():\n    return 'changed'\n",
        encoding="utf-8",
    )

    res = runner.invoke(
        app,
        ["understand", str(target), "--format", "json", "--changed"],
    )
    assert res.exit_code == 0

    payload = json.loads(res.stdout)
    assert payload["slice"]["changed_only"] is True
    paths = [item["path"] for item in payload["relevance"]]
    assert "src/app/utils.py" in paths
    assert "src/app/core.py" in paths
    assert "src/app/other.py" not in paths

    compact = (target / "docs" / "ai" / "repomap.compact.md").read_text(
        encoding="utf-8"
    )
    assert "Mode: `changed`" in compact


def test_understand_updates_existing_compact_repomap_without_duplicate_end_marker(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    _copy_fixture(FIXTURES / "python_uv", target)
    (target / "src" / "app").mkdir(parents=True, exist_ok=True)
    (target / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (target / "src" / "app" / "core.py").write_text(
        "from .utils import helper\n\n\ndef run():\n    return helper()\n",
        encoding="utf-8",
    )
    (target / "src" / "app" / "utils.py").write_text(
        "def helper():\n    return 'ok'\n",
        encoding="utf-8",
    )
    compact_path = target / "docs" / "ai" / "repomap.compact.md"
    compact_path.parent.mkdir(parents=True, exist_ok=True)
    compact_path.write_text(
        "\n".join(
            [
                "# Repo Map (Compact)",
                "",
                "<!-- AGENTSGEN:START section=repomap_compact -->",
                "- stale",
                "<!-- AGENTSGEN:END section=repomap_compact -->",
                "",
            ]
        ),
        encoding="utf-8",
    )

    res = runner.invoke(
        app,
        ["understand", str(target), "--format", "json", "--focus", "helper"],
    )
    assert res.exit_code == 0

    compact = compact_path.read_text(encoding="utf-8")
    assert compact.count("<!-- AGENTSGEN:START section=repomap_compact -->") == 1
    assert compact.count("<!-- AGENTSGEN:END section=repomap_compact -->") == 1
    assert "Focus: `helper`" in compact
