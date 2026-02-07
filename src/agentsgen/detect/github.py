from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CiInfo:
    ci_dir: str
    workflows: list[str]


def detect_github_actions(repo: Path) -> CiInfo | None:
    d = repo / ".github" / "workflows"
    if not d.is_dir():
        return None
    workflows = sorted([str(p.relative_to(repo)) for p in d.glob("*.yml") if p.is_file()] + [str(p.relative_to(repo)) for p in d.glob("*.yaml") if p.is_file()])
    return CiInfo(ci_dir=".github/workflows/", workflows=workflows)

