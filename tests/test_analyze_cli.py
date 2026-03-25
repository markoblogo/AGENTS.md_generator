from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agentsgen import analyze as analyze_module
from agentsgen.cli import app


runner = CliRunner()


def _mock_fetch(url: str, *, timeout: float = 10.0) -> analyze_module.UrlFetch:
    del timeout
    html = """
    <html>
      <head>
        <title>Example site</title>
        <meta name="description" content="AI-friendly site." />
        <script type="application/ld+json">{"@type":"WebSite"}</script>
      </head>
      <body>
        <main>
          <article>
            <section>
              <h1>Example</h1>
              <h2>Docs</h2>
              <h3>Guide</h3>
              <p>{content}</p>
            </section>
          </article>
        </main>
      </body>
    </html>
    """.replace("{content}", "word " * 320)
    return analyze_module.UrlFetch(
        url=url,
        status=200,
        text=html,
        headers={"content-type": "text/html"},
    )


def test_analyze_writes_llmo_score_json(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    monkeypatch.setattr(analyze_module, "_fetch_url", _mock_fetch)
    monkeypatch.setattr(analyze_module, "_probe_url", lambda url, timeout=10.0: True)

    res = runner.invoke(
        app, ["analyze", "https://example.com", str(target), "--format", "json"]
    )
    assert res.exit_code == 0

    payload = json.loads(res.stdout)
    assert payload["command"] == "analyze"
    assert payload["result"]["version"] == 1
    assert payload["result"]["generated_by"] == "agentsgen"
    assert payload["result"]["url"] == "https://example.com"
    assert payload["result"]["score"] > 0
    assert payload["result"]["recommendations"]

    output_path = target / "docs" / "ai" / "llmo-score.json"
    assert output_path.is_file()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["version"] == 1
    assert written["generated_by"] == "agentsgen"
    assert written["generated_at"].endswith("Z")


def test_analyze_use_ai_requires_api_key(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()

    res = runner.invoke(
        app, ["analyze", "https://example.com", str(target), "--use-ai"]
    )
    assert res.exit_code == 1
    assert "OPENAI_API_KEY is required" in res.stderr


def test_analyze_preserves_user_json_and_writes_generated_sibling(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "repo"
    output_dir = target / "docs" / "ai"
    output_dir.mkdir(parents=True)
    output_path = output_dir / "llmo-score.json"
    output_path.write_text('{"owner":"user"}\n', encoding="utf-8")

    monkeypatch.setattr(analyze_module, "_fetch_url", _mock_fetch)
    monkeypatch.setattr(analyze_module, "_probe_url", lambda url, timeout=10.0: False)

    res = runner.invoke(app, ["analyze", "https://example.com", str(target)])
    assert res.exit_code == 0

    assert json.loads(output_path.read_text(encoding="utf-8")) == {"owner": "user"}
    generated_path = output_dir / "llmo-score.generated.json"
    assert generated_path.is_file()
    generated = json.loads(generated_path.read_text(encoding="utf-8"))
    assert generated["generated_by"] == "agentsgen"
