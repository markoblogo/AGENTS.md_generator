from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Any

from ..config import ToolConfig


@dataclass(frozen=True)
class PresetInfo:
    name: str
    description: str
    example: str


_DEF_PACKAGE = __name__
_PRESET_SUFFIX = ".agentsgen.json"


def _preset_path(name: str):
    return resources.files(_DEF_PACKAGE).joinpath(f"{name}{_PRESET_SUFFIX}")


def preset_names() -> list[str]:
    names: list[str] = []
    for entry in resources.files(_DEF_PACKAGE).iterdir():
        if entry.is_file() and entry.name.endswith(_PRESET_SUFFIX):
            names.append(entry.name[: -len(_PRESET_SUFFIX)])
    return sorted(names)


def load_preset_data(name: str) -> dict[str, Any]:
    path = _preset_path(name)
    if not path.is_file():
        raise KeyError(name)
    return json.loads(path.read_text(encoding="utf-8"))


def list_presets() -> list[PresetInfo]:
    rows: list[PresetInfo] = []
    for name in preset_names():
        data = load_preset_data(name)
        rows.append(
            PresetInfo(
                name=name,
                description=str(data.get("description", "")).strip(),
                example=str(
                    data.get("example", f"agentsgen init . --preset {name}")
                ).strip(),
            )
        )
    return rows


def load_preset_config(name: str) -> ToolConfig:
    data = load_preset_data(name)
    config = dict(data.get("config", {}) or {})
    presets = dict(config.get("presets", {}) or {})
    presets.setdefault("selected", name)
    config["presets"] = presets
    return ToolConfig.from_json(config)
