from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .fs import safe_read_text


PYTHON_SENTINELS = [
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "pytest.ini",
    "tox.ini",
]


@dataclass(frozen=True)
class PythonInfo:
    toolchain: str  # uv|poetry|vanilla
    has_pyproject: bool
    has_ruff: bool
    has_black: bool
    has_mypy: bool
    has_pytest: bool
    evidence: list[str]


def _toml_has_table(text: str, table: str) -> bool:
    # Cheap check without a full TOML parse (we still parse for poetry/uv when present elsewhere).
    needle = f"[{table}]"
    return needle in text


def detect_python(repo: Path) -> PythonInfo | None:
    evidence: list[str] = []
    has_any = False
    for f in PYTHON_SENTINELS:
        if (repo / f).is_file():
            has_any = True
            evidence.append(f)
    if not has_any:
        return None

    pyproject = repo / "pyproject.toml"
    pyproject_text = safe_read_text(pyproject) if pyproject.is_file() else ""

    toolchain = "vanilla"
    if (repo / "uv.lock").is_file() or "[tool.uv]" in pyproject_text:
        toolchain = "uv"
        if (repo / "uv.lock").is_file():
            evidence.append("uv.lock")
        else:
            evidence.append("pyproject.toml:[tool.uv]")
    elif (repo / "poetry.lock").is_file() or "[tool.poetry]" in pyproject_text:
        toolchain = "poetry"
        if (repo / "poetry.lock").is_file():
            evidence.append("poetry.lock")
        else:
            evidence.append("pyproject.toml:[tool.poetry]")

    has_ruff = (repo / "ruff.toml").is_file() or "[tool.ruff]" in pyproject_text
    if has_ruff:
        evidence.append("ruff.toml" if (repo / "ruff.toml").is_file() else "pyproject.toml:[tool.ruff]")

    has_black = "[tool.black]" in pyproject_text
    if has_black:
        evidence.append("pyproject.toml:[tool.black]")

    has_mypy = (repo / "mypy.ini").is_file() or "[tool.mypy]" in pyproject_text
    if has_mypy:
        evidence.append("mypy.ini" if (repo / "mypy.ini").is_file() else "pyproject.toml:[tool.mypy]")

    has_pytest = (repo / "pytest.ini").is_file() or "[tool.pytest" in pyproject_text or "[tool.pytest.ini_options]" in pyproject_text
    if has_pytest:
        evidence.append("pytest.ini" if (repo / "pytest.ini").is_file() else "pyproject.toml:pytest")

    return PythonInfo(
        toolchain=toolchain,
        has_pyproject=pyproject.is_file(),
        has_ruff=has_ruff,
        has_black=has_black,
        has_mypy=has_mypy,
        has_pytest=has_pytest,
        evidence=sorted(set(evidence)),
    )


def commands_from_python(info: PythonInfo) -> dict[str, str]:
    # Priority below Makefile and node scripts; here we only fill if reasonably confident.
    cmds: dict[str, str] = {}

    runner = ""
    if info.toolchain == "uv":
        runner = "uv run "
    elif info.toolchain == "poetry":
        runner = "poetry run "

    if info.has_pytest:
        cmds["test"] = f"{runner}pytest".strip()
        cmds["fast"] = f"{runner}pytest -q".strip()
    # Lint/format/typecheck only when tool config exists.
    if info.has_ruff:
        cmds["lint"] = f"{runner}ruff check .".strip()
        cmds["format"] = f"{runner}ruff format .".strip()
    elif info.has_black:
        cmds["format"] = f"{runner}black .".strip()
    if info.has_mypy:
        cmds["typecheck"] = f"{runner}mypy .".strip()

    return cmds

