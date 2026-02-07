from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .fs import safe_read_text


@dataclass(frozen=True)
class NodeInfo:
    package_manager: str  # pnpm|yarn|npm
    scripts: dict[str, str]
    evidence: list[str]


def detect_node(repo: Path) -> NodeInfo | None:
    pkg = repo / "package.json"
    if not pkg.is_file():
        return None

    evidence: list[str] = ["package.json"]

    pm = "npm"
    if (repo / "pnpm-lock.yaml").is_file():
        pm = "pnpm"
        evidence.append("pnpm-lock.yaml")
    elif (repo / "yarn.lock").is_file():
        pm = "yarn"
        evidence.append("yarn.lock")
    elif (repo / "package-lock.json").is_file():
        pm = "npm"
        evidence.append("package-lock.json")

    scripts: dict[str, str] = {}
    try:
        d = json.loads(safe_read_text(pkg))
        scr = d.get("scripts", {}) or {}
        for k, v in scr.items():
            if isinstance(k, str) and isinstance(v, str):
                scripts[k] = v
    except Exception:
        pass

    return NodeInfo(package_manager=pm, scripts=scripts, evidence=sorted(set(evidence)))


def commands_from_node(info: NodeInfo) -> dict[str, str]:
    pm = info.package_manager
    scripts = info.scripts
    cmds: dict[str, str] = {}

    def run(script: str) -> str:
        if pm == "npm":
            if script == "test":
                return "npm test"
            return f"npm run {script}"
        if pm == "yarn":
            return f"yarn {script}"
        return f"pnpm {script}"

    for key in ["dev", "test", "lint", "build", "format", "typecheck"]:
        if key in scripts:
            cmds[key] = run(key)

    # fast check: prefer explicit scripts.
    for k in ["test:fast", "test:unit"]:
        if k in scripts:
            cmds["fast"] = run(k) if pm == "npm" else (f"{pm} {k}" if pm != "npm" else f"npm run {k}")
            break

    return cmds

