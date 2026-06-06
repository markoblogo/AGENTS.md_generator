from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileResult:
    path: Path
    action: str  # created|updated|skipped|generated|error
    message: str = ""
    changed: bool = False
    diff: str = ""


@dataclass(frozen=True)
class StatusFileReport:
    present: bool
    markers: bool
    marker_sections: int
    generated_sibling: bool


@dataclass(frozen=True)
class RepoStatusReport:
    status: str
    path: str
    config: dict[str, bool]
    agents_md: StatusFileReport
    runbook_md: StatusFileReport
    pack: dict[str, object]
    generated: dict[str, object]
    summary: dict[str, int]

    def to_json(self) -> dict[str, object]:
        return {
            "status": self.status,
            "path": self.path,
            "config": dict(self.config),
            "agents_md": asdict(self.agents_md),
            "runbook_md": asdict(self.runbook_md),
            "pack": dict(self.pack),
            "generated": dict(self.generated),
            "summary": dict(self.summary),
        }


@dataclass(frozen=True)
class AggregatedCheckReport:
    version: int
    command: str
    path: str
    status: str
    checks: dict[str, object]
    summary: dict[str, object]

    def to_json(self) -> dict[str, object]:
        return {
            "version": self.version,
            "command": self.command,
            "path": self.path,
            "status": self.status,
            "checks": self.checks,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class ReadmeSnippet:
    name: str
    start_line: int
    end_line: int
    content: str


@dataclass(frozen=True)
class ReadmeSnippetsReport:
    status: str
    check: bool
    dry_run: bool
    format_version: int
    readme_path: str
    output_path: str
    snippets_count: int
    snippets: list[ReadmeSnippet]
    diff: str = ""
    message: str = ""

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "check": self.check,
            "dry_run": self.dry_run,
            "format_version": self.format_version,
            "readme_path": self.readme_path,
            "output_path": self.output_path,
            "snippets_count": self.snippets_count,
            "snippets": [asdict(s) for s in self.snippets],
        }
        if self.diff:
            payload["diff"] = self.diff
        if self.message:
            payload["message"] = self.message
        return payload
