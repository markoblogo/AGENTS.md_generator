from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agentsgen.cli import app


runner = CliRunner()


def _write_readme(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_snippets_extracts_two_blocks_and_writes_output(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _write_readme(
        target / "README.md",
        "# Demo\n\n<!-- AGENTSGEN:SNIPPET name=install -->\npip install -e .\n<!-- AGENTSGEN:ENDSNIPPET -->\n\n<!-- AGENTSGEN:SNIPPET name=test -->\npytest -q\n<!-- AGENTSGEN:ENDSNIPPET -->\n",
    )

    res = runner.invoke(app, ["snippets", str(target)])
    assert res.exit_code == 0
    out = (target / "README_SNIPPETS.generated.md").read_text(encoding="utf-8")
    assert "# README Snippets (generated)" in out
    assert "## install" in out
    assert "pip install -e ." in out
    assert "## test" in out
    assert "pytest -q" in out


def test_snippets_check_detects_drift(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _write_readme(
        target / "README.md",
        "<!-- AGENTSGEN:SNIPPET name=install -->\npip install -e .\n<!-- AGENTSGEN:ENDSNIPPET -->\n",
    )
    (target / "README_SNIPPETS.generated.md").write_text("stale\n", encoding="utf-8")

    res = runner.invoke(app, ["snippets", str(target), "--check", "--format", "json"])
    assert res.exit_code == 1
    payload = json.loads(res.stdout)
    assert payload["status"] == "drift"
    assert payload["check"] is True
    assert payload["snippets_count"] == 1


def test_snippets_errors_on_duplicate_names(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _write_readme(
        target / "README.md",
        "<!-- AGENTSGEN:SNIPPET name=dup -->\na\n<!-- AGENTSGEN:ENDSNIPPET -->\n<!-- AGENTSGEN:SNIPPET name=dup -->\nb\n<!-- AGENTSGEN:ENDSNIPPET -->\n",
    )

    res = runner.invoke(app, ["snippets", str(target), "--format", "json"])
    assert res.exit_code == 2
    payload = json.loads(res.stdout)
    assert payload["status"] == "error"
    assert "Duplicate snippet name" in payload["message"]


def test_snippets_errors_on_unclosed_snippet(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _write_readme(
        target / "README.md",
        "<!-- AGENTSGEN:SNIPPET name=install -->\npip install -e .\n",
    )

    res = runner.invoke(app, ["snippets", str(target), "--format", "json"])
    assert res.exit_code == 2
    payload = json.loads(res.stdout)
    assert payload["status"] == "error"
    assert "no matching ENDSNIPPET" in payload["message"]


def test_snippets_no_snippets_found_ok_and_no_output(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _write_readme(target / "README.md", "# Demo\n")

    res = runner.invoke(app, ["snippets", str(target)])
    assert res.exit_code == 0
    assert "no snippets found" in res.stdout
    assert not (target / "README_SNIPPETS.generated.md").exists()
