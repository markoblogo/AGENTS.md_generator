from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .fs import safe_read_text


TARGET_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_\-\.]*)\s*:(?![=])")


@dataclass(frozen=True)
class MakefileInfo:
    path: str
    targets: list[str]


def parse_makefile_targets(repo: Path) -> MakefileInfo | None:
    for name in ["Makefile", "makefile", "GNUmakefile"]:
        p = repo / name
        if not p.is_file():
            continue
        text = safe_read_text(p)
        targets: set[str] = set()
        for line in text.splitlines():
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue
            m = TARGET_RE.match(line)
            if not m:
                continue
            t = m.group(1)
            if t.startswith("."):
                continue
            if t == "%":
                continue
            targets.add(t)
        return MakefileInfo(path=name, targets=sorted(targets))
    return None

