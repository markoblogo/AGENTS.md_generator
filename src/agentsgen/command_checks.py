"""Read-only checks of configured command references. Never execute commands."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

from .config import ToolConfig


def check_command_references(
    target: Path, cfg: ToolConfig
) -> tuple[list[str], list[str]]:
    problems: list[str] = []
    warnings: list[str] = []
    for label, command in cfg.project_info.commands.items():
        try:
            words = shlex.split(command)
        except ValueError:
            problems.append(f"commands.{label}: invalid shell quoting")
            continue
        prefix = f"commands.{label} ({command})"
        if not words:
            continue
        # Compound commands and wrappers need human review; don't infer execution.
        if re.search(r"[;&|<>`$\n]", command):
            warnings.append(f"{prefix}: not verified (compound or dynamic command)")
            continue
        tool, *args = words
        script = None
        if tool in ("npm", "pnpm", "yarn") and args:
            if args[0] == "run" and len(args) > 1 and not args[1].startswith("-"):
                script = args[1]
            elif args[0] in (
                "test",
                "start",
                "dev",
                "build",
                "lint",
                "format",
                "typecheck",
            ):
                script = args[0]
        if script:
            manifest = target / "package.json"
            try:
                payload = json.loads(manifest.read_text(encoding="utf-8"))
                scripts = payload.get("scripts", {})
                if not isinstance(scripts, dict):
                    raise ValueError("scripts must be an object")
            except (OSError, ValueError, AttributeError) as exc:
                problems.append(f"{prefix}: cannot read package.json ({exc})")
                continue
            if script not in scripts:
                problems.append(
                    f"{prefix}: package.json has no script '{script}'; review .agentsgen.json"
                )
        elif (
            tool == "make"
            and args
            and all(
                re.fullmatch(r"[\w.-]+", arg) and not arg.startswith("-")
                for arg in args
            )
        ):
            makefile = next(
                (
                    target / name
                    for name in ("GNUmakefile", "makefile", "Makefile")
                    if (target / name).is_file()
                ),
                None,
            )
            if makefile is None:
                problems.append(f"{prefix}: no Makefile exists; review .agentsgen.json")
                continue
            body = makefile.read_text(encoding="utf-8")
            targets: set[str] = set()
            for match in re.finditer(
                r"^([^\s#:=][^:=\n]*):(?![=])", body, re.MULTILINE
            ):
                targets.update(match[1].split())
            dynamic = bool(re.search(r"(?m)^\s*-?include\s|[$%]", body))
            for name in args:
                if name not in targets:
                    if dynamic:
                        warnings.append(
                            f"{prefix}: target '{name}' not verified (dynamic Makefile)"
                        )
                    else:
                        problems.append(
                            f"{prefix}: Makefile has no target '{name}'; review .agentsgen.json"
                        )
        else:
            warnings.append(f"{prefix}: not verified (unsupported command form)")
    for location in cfg.project_info.config_locations:
        if any(char in location for char in "*?[]$"):
            warnings.append(f"config path {location}: not verified (pattern)")
        elif not (target / location).exists():
            problems.append(f"config path {location}: missing; review .agentsgen.json")
    return problems, warnings
