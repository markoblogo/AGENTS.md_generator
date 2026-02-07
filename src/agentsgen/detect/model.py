from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Evidence:
    python: list[str] = field(default_factory=list)
    node: list[str] = field(default_factory=list)
    make: list[str] = field(default_factory=list)
    ci: list[str] = field(default_factory=list)


@dataclass
class DetectResult:
    project: dict[str, Any] = field(default_factory=dict)
    paths: dict[str, Any] = field(default_factory=dict)
    commands: dict[str, str] = field(default_factory=dict)
    evidence: Evidence = field(default_factory=Evidence)

    def to_json(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "paths": self.paths,
            "commands": self.commands,
            "evidence": {
                "python": self.evidence.python,
                "node": self.evidence.node,
                "make": self.evidence.make,
                "ci": self.evidence.ci,
            },
        }

