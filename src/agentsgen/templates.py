from __future__ import annotations

from pathlib import Path


def templates_base_dir() -> Path:
    # Python 3.11: importlib.resources.files returns a Traversable.
    import importlib.resources as resources

    base = resources.files("agentsgen").joinpath("templates")
    return Path(str(base))


def prompt_template_path(name: str) -> Path:
    return templates_base_dir() / "common" / "prompts" / name


def pack_template_path(stack: str, name: str) -> Path:
    return templates_base_dir() / "pack" / stack / name
