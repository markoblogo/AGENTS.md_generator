from __future__ import annotations

from pathlib import Path


def safe_read_text(path: Path, *, max_bytes: int = 256 * 1024) -> str:
    data = path.read_bytes()
    if len(data) > max_bytes:
        data = data[:max_bytes]
    return data.decode("utf-8", errors="replace")


def exists_any(target: Path, names: list[str]) -> bool:
    for n in names:
        if (target / n).exists():
            return True
    return False


def list_files(target: Path, rel_dir: str) -> list[str]:
    d = target / rel_dir
    if not d.is_dir():
        return []
    out: list[str] = []
    for p in sorted(d.rglob("*")):
        if p.is_file():
            out.append(str(p.relative_to(target)))
    return out

