from __future__ import annotations

from pathlib import Path

from .config import ToolConfig
from .constants import CONFIG_FILENAME
from .io_utils import read_json, write_json_atomic


def load_tool_config(target: Path) -> ToolConfig:
    return ToolConfig.from_json(read_json(target / CONFIG_FILENAME))


def save_tool_config(target: Path, cfg: ToolConfig) -> None:
    write_json_atomic(target / CONFIG_FILENAME, cfg.to_json())
