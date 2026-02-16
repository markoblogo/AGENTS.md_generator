from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .model import ProjectInfo
from .detect.model import DetectResult
from .constants import DEFAULT_PACK_OUTPUT_DIR, DEFAULT_PACK_LLMS_FORMAT


@dataclass(frozen=True)
class ToolMarkers:
    start: str = "<!-- AGENTSGEN:START section={section} -->"
    end: str = "<!-- AGENTSGEN:END section={section} -->"


@dataclass
class ToolPack:
    enabled: bool = True
    llms_format: str = DEFAULT_PACK_LLMS_FORMAT  # txt|md
    output_dir: str = DEFAULT_PACK_OUTPUT_DIR
    files: list[str] = field(default_factory=list)


@dataclass
class ToolConfig:
    # v1 schema (recommended). We also support reading legacy ProjectInfo-only configs.
    version: int = 1

    mode: str = "safe"
    on_missing_markers: str = "write_generated"
    generated_suffix: str = ".generated"

    markers: ToolMarkers = field(default_factory=ToolMarkers)

    # Which sections are expected in AGENTS.md (and which stack section to include).
    sections: list[str] = field(
        default_factory=lambda: [
            "guardrails",
            "workflow",
            "style",
            "verification",
            "stack",
            "repo_context",
        ]
    )

    presets: dict[str, Any] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)

    # Template context. Keep structure close to the proposed .agentsgen.json schema.
    project: dict[str, Any] = field(default_factory=dict)
    paths: dict[str, Any] = field(default_factory=dict)
    commands: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    pack: ToolPack = field(default_factory=ToolPack)

    # Back-compat + internal convenience for stack templates/summary.
    project_info: ProjectInfo = field(
        default_factory=lambda: ProjectInfo(
            project_name="", stack="static"
        ).normalized()
    )

    def to_json(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "mode": self.mode,
            "on_missing_markers": self.on_missing_markers,
            "generated_suffix": self.generated_suffix,
            "markers": {"start": self.markers.start, "end": self.markers.end},
            "sections": list(self.sections),
            "presets": self.presets,
            "defaults": self.defaults,
            "project": self.project,
            "paths": self.paths,
            "commands": self.commands,
            "evidence": self.evidence,
            "pack": {
                "enabled": self.pack.enabled,
                "llms_format": self.pack.llms_format,
                "output_dir": self.pack.output_dir,
                "files": list(self.pack.files),
            },
        }

    @staticmethod
    def from_json(d: dict[str, Any]) -> "ToolConfig":
        # Legacy format: ProjectInfo-only dict (no version field).
        if "version" not in d and "project_name" in d and "stack" in d:
            info = ProjectInfo.from_json(d)
            cfg = ToolConfig(project_info=info)
            cfg.project = {
                "name": info.project_name,
                "primary_stack": info.stack,
                "repo_root": ".",
            }
            return cfg

        cfg = ToolConfig()
        cfg.version = int(d.get("version", 1))
        cfg.mode = str(d.get("mode", "safe"))
        cfg.on_missing_markers = str(d.get("on_missing_markers", "write_generated"))
        cfg.generated_suffix = str(d.get("generated_suffix", ".generated"))

        m = d.get("markers", {}) or {}
        cfg.markers = ToolMarkers(
            start=str(m.get("start", cfg.markers.start)),
            end=str(m.get("end", cfg.markers.end)),
        )

        cfg.sections = list(d.get("sections", cfg.sections) or cfg.sections)
        cfg.presets = dict(d.get("presets", {}) or {})
        cfg.defaults = dict(d.get("defaults", {}) or {})

        cfg.project = dict(d.get("project", {}) or {})
        cfg.paths = dict(d.get("paths", {}) or {})
        cfg.commands = dict(d.get("commands", {}) or {})
        cfg.evidence = dict(d.get("evidence", {}) or {})
        p = dict(d.get("pack", {}) or {})
        cfg.pack = ToolPack(
            enabled=bool(p.get("enabled", True)),
            llms_format=str(p.get("llms_format", DEFAULT_PACK_LLMS_FORMAT)),
            output_dir=str(p.get("output_dir", DEFAULT_PACK_OUTPUT_DIR)),
            files=list(p.get("files", []) or []),
        )

        # Derive internal ProjectInfo for existing render pipeline.
        project_name = str(cfg.project.get("name", "")) or ""
        primary_stack = str(cfg.project.get("primary_stack", "")) or ""
        stack_for_templates = (
            primary_stack if primary_stack in ("python", "node", "static") else "static"
        )

        info = ProjectInfo(
            project_name=project_name or "", stack=stack_for_templates
        ).normalized()
        # Structure hints from detection/config.
        sd = cfg.paths.get("source_dirs", []) if isinstance(cfg.paths, dict) else []
        cl = (
            cfg.paths.get("config_locations", []) if isinstance(cfg.paths, dict) else []
        )
        if isinstance(sd, list):
            info.source_dirs = [str(x) for x in sd if str(x).strip()]
        if isinstance(cl, list):
            info.config_locations = [str(x) for x in cl if str(x).strip()]

        # Preserve derived details where available.
        if "node_package_manager" in cfg.project:
            info.package_manager = str(cfg.project.get("node_package_manager") or "")
        if "python_toolchain" in cfg.project:
            info.python_tooling = str(cfg.project.get("python_toolchain") or "")
        # Map detected commands into ProjectInfo (only the keys it uses).
        for k in [
            "install",
            "dev",
            "test",
            "lint",
            "format",
            "build",
            "typecheck",
            "fast",
            "full",
        ]:
            v = str(cfg.commands.get(k, "") or "").strip()
            if v:
                info.commands[k] = v
        cfg.project_info = info.normalized()
        return cfg

    @staticmethod
    def from_project_info(info: ProjectInfo) -> "ToolConfig":
        cfg = ToolConfig()
        cfg.project_info = info.normalized()
        cfg.project = {
            "name": cfg.project_info.project_name,
            "primary_stack": cfg.project_info.stack,
            "repo_root": ".",
        }
        cfg.commands = dict(cfg.project_info.commands)
        cfg.pack = ToolPack()
        return cfg

    @staticmethod
    def from_detect(det: DetectResult) -> "ToolConfig":
        cfg = ToolConfig()
        cfg.project = dict(det.project or {})
        cfg.paths = dict(det.paths or {})
        cfg.commands = dict(det.commands or {})
        cfg.evidence = det.to_json().get("evidence", {})
        cfg.pack = ToolPack()
        # Derive ProjectInfo using existing parser logic.
        cfg = ToolConfig.from_json(cfg.to_json())
        return cfg
