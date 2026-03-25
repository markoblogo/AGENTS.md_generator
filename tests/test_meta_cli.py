from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agentsgen import meta as meta_module
from agentsgen.analyze import UrlFetch
from agentsgen.cli import app


runner = CliRunner()


def _mock_fetch(url: str, *, timeout: float = 10.0) -> UrlFetch:
    del timeout
    html = """
    <html>
      <head>
        <title>Example product</title>
        <meta name="description" content="Helpful AI-focused product site." />
      </head>
      <body>
        <main>
          <h1>Example</h1>
          <p>{content}</p>
        </main>
      </body>
    </html>
    """.replace("{content}", "word " * 180)
    return UrlFetch(
        url=url,
        status=200,
        text=html,
        headers={"content-type": "text/html"},
    )


def test_meta_writes_llmo_meta_json(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    monkeypatch.setattr(meta_module, "_fetch_url", _mock_fetch)
    monkeypatch.setattr(
        meta_module,
        "_openai_chat_json",
        lambda **kwargs: {
            "title": "Example product for AI",
            "description": "A concise description for AI visibility.",
            "keywords": ["ai", "docs", "seo", "metadata", "product"],
            "shortDescription": "Short listing description.",
        },
    )

    res = runner.invoke(
        app, ["meta", "https://example.com", str(target), "--format", "json"]
    )
    assert res.exit_code == 0

    payload = json.loads(res.stdout)
    assert payload["command"] == "meta"
    assert payload["result"]["version"] == 1
    assert payload["result"]["generated_by"] == "agentsgen"
    assert payload["result"]["result"]["title"] == "Example product for AI"

    output_path = target / "docs" / "ai" / "llmo-meta.json"
    assert output_path.is_file()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["generated_by"] == "agentsgen"
    assert written["result"]["keywords"] == [
        "ai",
        "docs",
        "seo",
        "metadata",
        "product",
    ]


def test_meta_requires_api_key(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()

    res = runner.invoke(app, ["meta", "https://example.com", str(target)])
    assert res.exit_code == 1
    assert "OPENAI_API_KEY is required" in res.stderr


def test_meta_preserves_user_json_and_writes_generated_sibling(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "repo"
    output_dir = target / "docs" / "ai"
    output_dir.mkdir(parents=True)
    output_path = output_dir / "llmo-meta.json"
    output_path.write_text('{"owner":"user"}\n', encoding="utf-8")

    monkeypatch.setattr(meta_module, "_fetch_url", _mock_fetch)
    monkeypatch.setattr(
        meta_module,
        "_openai_chat_json",
        lambda **kwargs: {
            "title": "Generated title",
            "description": "Generated description",
            "keywords": ["one", "two", "three", "four", "five"],
            "shortDescription": "Generated short description",
        },
    )

    res = runner.invoke(app, ["meta", "https://example.com", str(target)])
    assert res.exit_code == 0

    assert json.loads(output_path.read_text(encoding="utf-8")) == {"owner": "user"}
    generated_path = output_dir / "llmo-meta.generated.json"
    assert generated_path.is_file()
    generated = json.loads(generated_path.read_text(encoding="utf-8"))
    assert generated["generated_by"] == "agentsgen"
