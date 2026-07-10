from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_SEED_PATH = Path("docs/ai/rabbithole.seed.md")
DEFAULT_CANDIDATES = (
    "AGENTS.md",
    "RUNBOOK.md",
    "docs/ai/repomap.compact.md",
    "docs/ai/architecture.md",
    "docs/ai/how-to-test.md",
    "docs/ai/id-context.json",
)


@dataclass(frozen=True)
class RabbitholeSeedResult:
    output_path: Path
    source_files: list[str]
    content: str
    dry_run: bool


def _read_excerpt(path: Path, max_chars: int) -> str:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n[truncated]"


def build_rabbithole_seed(
    repo: Path,
    *,
    max_chars_per_file: int = 6000,
    candidates: tuple[str, ...] = DEFAULT_CANDIDATES,
) -> tuple[str, list[str]]:
    repo = repo.resolve()
    included: list[tuple[str, str]] = []
    for rel in candidates:
        path = repo / rel
        if path.is_file():
            included.append((rel, _read_excerpt(path, max_chars=max_chars_per_file)))

    lines = [
        "# Rabbithole Seed",
        "",
        "Use this as a local Rabbithole starting document for interactive repo exploration.",
        "",
        "Suggested flow:",
        "",
        "1. Open this document with the Rabbithole MCP server.",
        "2. Select unclear or high-risk passages.",
        "3. Ask focused questions before changing repo contracts, skills, or SET plans.",
        "4. Promote durable answers back into repo docs only when they are broadly useful.",
        "",
        "Rabbithole is optional. This file is a navigation aid, not a source of truth.",
        "",
        "## Suggested Review Lenses",
        "",
        "- `assumption-excavation`: surface hidden assumptions in repo contracts and plans.",
        "- `pipeline-readiness-gate`: choose a compact pre/post/ship gate for the work.",
        "- `confidence-fragility-review`: check whether confident claims are backed by evidence.",
        "- `reversible-agent-task`: keep risky agent output in a proposal/worktree until inspect -> select/apply/discard.",
        "",
        "## Source Files",
        "",
    ]
    if included:
        lines.extend(f"- `{rel}`" for rel, _ in included)
    else:
        lines.append("- No standard agentsgen context files found.")

    for rel, excerpt in included:
        lines.extend([
            "",
            f"## {rel}",
            "",
            "```text",
            excerpt,
            "```",
        ])
    return "\n".join(lines).rstrip() + "\n", [rel for rel, _ in included]


def write_rabbithole_seed(
    repo: Path,
    *,
    output_path: Path | None = None,
    max_chars_per_file: int = 6000,
    dry_run: bool = False,
) -> RabbitholeSeedResult:
    repo = repo.resolve()
    resolved_output = output_path or repo / DEFAULT_SEED_PATH
    if not resolved_output.is_absolute():
        resolved_output = repo / resolved_output
    content, source_files = build_rabbithole_seed(
        repo,
        max_chars_per_file=max_chars_per_file,
    )
    if not dry_run:
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        resolved_output.write_text(content, encoding="utf-8")
    return RabbitholeSeedResult(
        output_path=resolved_output,
        source_files=source_files,
        content=content,
        dry_run=dry_run,
    )
