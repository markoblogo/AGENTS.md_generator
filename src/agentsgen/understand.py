from __future__ import annotations

import ast
import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .actions import (
    FileResult,
    _generated_sibling_path,
    _handle_file,
    _unified_diff,
)
from .detect import detect_repo
from .io_utils import read_text, write_text_atomic
from .markers import validate_markers
from .normalize import normalize_markdown

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".turbo",
    ".pytest_cache",
    ".mypy_cache",
}

_CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
}

_LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".json": "json",
    ".md": "markdown",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
}
_TEXT_FILENAMES = {
    "README",
    "README.md",
    "AGENTS.md",
    "RUNBOOK.md",
    "Makefile",
    "makefile",
}
_VISIBLE_HIDDEN_NAMES = {".github", ".agentsgen.json"}

_JS_IMPORT_RE = re.compile(
    r"""(?:
        import\s+.*?\s+from\s+["'](?P<import_from>[^"']+)["']|
        import\s+["'](?P<import_only>[^"']+)["']|
        require\(\s*["'](?P<require>[^"']+)["']\s*\)|
        export\s+.*?\s+from\s+["'](?P<export_from>[^"']+)["']
    )""",
    re.VERBOSE,
)
_JS_SYMBOL_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function|class)\s+\w+|^\s*(?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?(?:\(|function)",
    re.MULTILINE,
)
_MAKE_TARGET_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*):")
_MERMAID_START = "%% AGENTSGEN:START section=graph"
_MERMAID_END = "%% AGENTSGEN:END section=graph"


@dataclass(frozen=True)
class RepoFileInfo:
    path: str
    size: int
    language: str
    symbols_count: int


@dataclass(frozen=True)
class ImportEdge:
    from_path: str
    to_path: str
    kind: str = "import"


@dataclass(frozen=True)
class RepoEntrypoint:
    label: str
    command: str
    source: str


@dataclass(frozen=True)
class RelevanceItem:
    path: str
    score: int
    signals: tuple[str, ...]
    distance_from_entrypoint: int | None
    changed: bool
    entrypoint: bool


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _stable_knowledge_payload(payload: dict[str, object]) -> str:
    clone = json.loads(json.dumps(payload))
    clone["generated_at"] = ""
    return json.dumps(clone, sort_keys=True, separators=(",", ":"))


def _rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _should_skip(path: Path, root: Path, output_dir: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    if any(part in _EXCLUDED_DIRS for part in rel_parts):
        return True
    if any(
        part.startswith(".") and part not in _VISIBLE_HIDDEN_NAMES for part in rel_parts
    ):
        return True
    if path.name in {"agents.knowledge.json", "agents.knowledge.generated.json"}:
        return True
    if output_dir in path.parents and path.name in {"repomap.md", "graph.mmd"}:
        return True
    return False


def _language_for_path(path: Path) -> str:
    return _LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "unknown")


def _count_symbols(path: Path, text: str) -> int:
    if path.suffix == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return 0
        return sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            for node in ast.walk(tree)
        )
    if path.suffix.lower() in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        return len(_JS_SYMBOL_RE.findall(text))
    return 0


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _source_roots(root: Path, detected_paths: dict[str, object]) -> list[Path]:
    roots: list[Path] = []
    for raw in list(detected_paths.get("source_dirs", []) or []):
        candidate = (root / str(raw)).resolve()
        if candidate.exists():
            roots.append(candidate)
    if not roots:
        roots.append(root.resolve())
    return roots


def _python_module_candidates(
    path: Path, root: Path, source_roots: list[Path]
) -> list[str]:
    candidates: list[str] = []
    for source_root in source_roots:
        try:
            rel = path.resolve().relative_to(source_root.resolve())
        except ValueError:
            continue
        parts = list(rel.parts)
        if not parts or path.suffix != ".py":
            continue
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = Path(parts[-1]).stem
        name = ".".join(part for part in parts if part)
        if name:
            candidates.append(name)
    try:
        rel = path.resolve().relative_to(root.resolve())
        parts = list(rel.parts)
        if parts and path.suffix == ".py":
            if parts[-1] == "__init__.py":
                parts = parts[:-1]
            else:
                parts[-1] = Path(parts[-1]).stem
            name = ".".join(part for part in parts if part)
            if name:
                candidates.append(name)
    except ValueError:
        pass
    return sorted(set(candidates))


def _build_python_module_map(
    files: list[Path], root: Path, source_roots: list[Path]
) -> dict[str, str]:
    module_map: dict[str, str] = {}
    for path in files:
        if path.suffix != ".py":
            continue
        rel = _rel(path, root)
        for candidate in _python_module_candidates(path, root, source_roots):
            module_map[candidate] = rel
    return module_map


def _resolve_python_import(
    current_path: Path,
    module_map: dict[str, str],
    root: Path,
    source_roots: list[Path],
    module: str | None,
    level: int,
) -> str | None:
    current_candidates = _python_module_candidates(current_path, root, source_roots)
    current_module = current_candidates[0] if current_candidates else ""
    current_parts = current_module.split(".") if current_module else []
    package_parts = (
        current_parts[:-1] if current_path.name != "__init__.py" else current_parts
    )

    if level > 0:
        if level - 1 > len(package_parts):
            return None
        base_parts = package_parts[: len(package_parts) - (level - 1)]
        if module:
            base_parts.extend([part for part in module.split(".") if part])
        resolved = ".".join(part for part in base_parts if part)
        return module_map.get(resolved)

    if module:
        return module_map.get(module)
    return None


def _resolve_js_import(current_path: Path, target_spec: str, root: Path) -> str | None:
    if not target_spec.startswith("."):
        return None
    base = (current_path.parent / target_spec).resolve()
    candidates = [
        base,
        *[base.with_suffix(ext) for ext in sorted(_CODE_EXTENSIONS)],
        base / "index.js",
        base / "index.ts",
        base / "index.tsx",
        base / "index.jsx",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            try:
                return _rel(candidate, root)
            except ValueError:
                return None
    return None


def _scan_imports(
    files: list[Path],
    *,
    root: Path,
    source_roots: list[Path],
) -> tuple[list[RepoFileInfo], list[ImportEdge]]:
    file_infos: list[RepoFileInfo] = []
    edges: list[ImportEdge] = []
    python_module_map = _build_python_module_map(files, root, source_roots)

    for path in sorted(files, key=lambda item: _rel(item, root)):
        text = read_text(path)
        rel_path = _rel(path, root)
        file_infos.append(
            RepoFileInfo(
                path=rel_path,
                size=path.stat().st_size,
                language=_language_for_path(path),
                symbols_count=_count_symbols(path, text),
            )
        )

        if path.suffix == ".py":
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            seen_targets: set[str] = set()
            for node in ast.walk(tree):
                target_rel: str | None = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        target_rel = _resolve_python_import(
                            path,
                            python_module_map,
                            root,
                            source_roots,
                            alias.name,
                            0,
                        )
                        if target_rel and target_rel not in seen_targets:
                            seen_targets.add(target_rel)
                            edges.append(ImportEdge(rel_path, target_rel))
                elif isinstance(node, ast.ImportFrom):
                    target_rel = _resolve_python_import(
                        path,
                        python_module_map,
                        root,
                        source_roots,
                        node.module,
                        node.level,
                    )
                    if target_rel and target_rel not in seen_targets:
                        seen_targets.add(target_rel)
                        edges.append(ImportEdge(rel_path, target_rel))
            continue

        if path.suffix.lower() in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
            seen_targets: set[str] = set()
            for match in _JS_IMPORT_RE.finditer(text):
                spec = next((value for value in match.groups() if value), "")
                target_rel = _resolve_js_import(path, spec, root)
                if target_rel and target_rel not in seen_targets:
                    seen_targets.add(target_rel)
                    edges.append(ImportEdge(rel_path, target_rel))

    edges = sorted(
        {(edge.from_path, edge.to_path, edge.kind) for edge in edges},
        key=lambda item: (item[0], item[1], item[2]),
    )
    return file_infos, [ImportEdge(*edge) for edge in edges]


def _top_level_structure(root: Path) -> list[str]:
    rows: list[str] = []
    for path in sorted(
        root.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())
    ):
        if path.name in _EXCLUDED_DIRS or path.name.startswith(".git"):
            continue
        if path.name.startswith(".") and path.name not in _VISIBLE_HIDDEN_NAMES:
            continue
        if path.name in {"agents.knowledge.json", "agents.knowledge.generated.json"}:
            continue
        suffix = "/" if path.is_dir() else ""
        rows.append(f"`{path.name}{suffix}`")
    return rows[:20]


def _entrypoints_from_config(root: Path) -> list[RepoEntrypoint]:
    cfg_path = root / ".agentsgen.json"
    if not cfg_path.exists():
        return []
    try:
        payload = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    commands = payload.get("commands", {})
    if not isinstance(commands, dict):
        return []
    rows = [
        RepoEntrypoint(label=str(key), command=str(value).strip(), source="manual")
        for key, value in commands.items()
        if str(value).strip()
    ]
    return sorted(rows, key=lambda item: item.label)


def _entrypoints_from_package_json(root: Path) -> list[RepoEntrypoint]:
    package_json = root / "package.json"
    if not package_json.exists():
        return []
    try:
        payload = json.loads(package_json.read_text(encoding="utf-8"))
    except Exception:
        return []
    scripts = payload.get("scripts", {})
    if not isinstance(scripts, dict):
        return []
    rows: list[RepoEntrypoint] = []
    package_manager = "npm"
    if (root / "pnpm-lock.yaml").exists():
        package_manager = "pnpm"
    elif (root / "yarn.lock").exists():
        package_manager = "yarn"
    for key, value in sorted(scripts.items()):
        command = str(value).strip()
        if not command:
            continue
        if package_manager == "pnpm":
            shell = "pnpm install" if key == "install" else f"pnpm {key}"
        elif package_manager == "yarn":
            shell = "yarn install" if key == "install" else f"yarn {key}"
        else:
            shell = "npm install" if key == "install" else f"npm run {key}"
        rows.append(
            RepoEntrypoint(label=str(key), command=shell, source="package.json")
        )
    return rows


def _entrypoints_from_makefile(root: Path) -> list[RepoEntrypoint]:
    for name in ("Makefile", "makefile"):
        path = root / name
        if not path.exists():
            continue
        targets: list[RepoEntrypoint] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            match = _MAKE_TARGET_RE.match(line)
            if not match:
                continue
            target = match.group(1)
            if target.startswith("."):
                continue
            targets.append(
                RepoEntrypoint(
                    label=target, command=f"make {target}", source="makefile"
                )
            )
        dedup = {(item.label, item.command, item.source): item for item in targets}
        return [dedup[key] for key in sorted(dedup)]
    return []


def _entrypoints_from_pyproject(root: Path) -> list[RepoEntrypoint]:
    path = root / "pyproject.toml"
    if not path.exists() or tomllib is None:
        return []
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    scripts = payload.get("project", {}).get("scripts", {}) or payload.get(
        "tool", {}
    ).get("poetry", {}).get("scripts", {})
    if not isinstance(scripts, dict):
        return []
    rows: list[RepoEntrypoint] = []
    for label in sorted(scripts):
        rows.append(
            RepoEntrypoint(label=str(label), command=str(label), source="pyproject")
        )
    return rows


def _detect_entrypoints(root: Path) -> list[RepoEntrypoint]:
    rows = _entrypoints_from_config(root)
    if rows:
        return rows
    rows = _entrypoints_from_package_json(root)
    if rows:
        return rows
    rows = _entrypoints_from_makefile(root)
    if rows:
        return rows
    return _entrypoints_from_pyproject(root)


def _git_changed_files(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return []
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--short",
                "--untracked-files=all",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if proc.returncode != 0:
        return []

    rows: set[str] = set()
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        raw = line[3:].strip()
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1].strip()
        if raw:
            rows.add(raw.replace("\\", "/"))
    return sorted(rows)


def _extract_command_file_hints(command: str, root: Path) -> list[str]:
    hints: list[str] = []
    for token in re.findall(r"[A-Za-z0-9_./-]+\.[A-Za-z0-9]+", command):
        candidate = (root / token).resolve()
        if candidate.exists() and candidate.is_file():
            try:
                hints.append(_rel(candidate, root))
            except ValueError:
                continue
    return sorted(set(hints))


def _default_entry_file_hints(file_infos: list[RepoFileInfo]) -> list[str]:
    preferred = (
        "src/main.py",
        "src/app.py",
        "src/cli.py",
        "main.py",
        "app.py",
        "cli.py",
        "src/index.ts",
        "src/index.tsx",
        "src/main.ts",
        "src/main.tsx",
        "src/index.js",
        "src/index.jsx",
        "index.ts",
        "index.tsx",
        "index.js",
        "index.jsx",
        "server.js",
        "server.ts",
    )
    available = {item.path for item in file_infos}
    return [path for path in preferred if path in available]


def _entrypoint_files(
    *,
    root: Path,
    file_infos: list[RepoFileInfo],
    entrypoints: list[RepoEntrypoint],
) -> list[str]:
    available = {item.path for item in file_infos}
    rows: list[str] = []
    for entry in entrypoints:
        rows.extend(_extract_command_file_hints(entry.command, root))
    if rows:
        return sorted({path for path in rows if path in available})
    return _default_entry_file_hints(file_infos)


def _rank_relevance(
    *,
    root: Path,
    file_infos: list[RepoFileInfo],
    edges: list[ImportEdge],
    entrypoints: list[RepoEntrypoint],
) -> tuple[list[RelevanceItem], list[str], list[str]]:
    changed_files = _git_changed_files(root)
    changed_set = set(changed_files)
    entrypoint_files = _entrypoint_files(
        root=root, file_infos=file_infos, entrypoints=entrypoints
    )
    entrypoint_set = set(entrypoint_files)
    inbound = Counter(edge.to_path for edge in edges)
    outbound = Counter(edge.from_path for edge in edges)
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.from_path, []).append(edge.to_path)

    distances: dict[str, int] = {}
    queue = list(entrypoint_files)
    for path in queue:
        distances[path] = 0
    index = 0
    while index < len(queue):
        current = queue[index]
        index += 1
        for neighbor in adjacency.get(current, []):
            if neighbor in distances:
                continue
            distances[neighbor] = distances[current] + 1
            queue.append(neighbor)

    rows: list[RelevanceItem] = []
    for item in file_infos:
        score = 0
        signals: list[str] = []
        if item.path in changed_set:
            score += 30
            signals.append("git-changed")
        if item.path in entrypoint_set:
            score += 24
            signals.append("entrypoint")
        distance = distances.get(item.path)
        if distance is not None:
            proximity_boost = {0: 18, 1: 12, 2: 8, 3: 4}.get(distance, 2)
            score += proximity_boost
            signals.append(f"hop-{distance}")
        inbound_count = inbound.get(item.path, 0)
        if inbound_count:
            score += inbound_count * 3
            signals.append(f"inbound:{inbound_count}")
        outbound_count = outbound.get(item.path, 0)
        if outbound_count:
            score += min(outbound_count, 4)
            signals.append(f"outbound:{outbound_count}")
        if item.symbols_count:
            score += min(item.symbols_count, 8)
            signals.append(f"symbols:{item.symbols_count}")
        if item.size:
            size_points = min(item.size // 1500, 6)
            if size_points:
                score += size_points
                signals.append(f"size:{item.size}")
        rows.append(
            RelevanceItem(
                path=item.path,
                score=score,
                signals=tuple(signals),
                distance_from_entrypoint=distance,
                changed=item.path in changed_set,
                entrypoint=item.path in entrypoint_set,
            )
        )

    ranked = sorted(rows, key=lambda item: (-item.score, item.path))
    return ranked, changed_files, entrypoint_files


def _key_modules(file_infos: list[RepoFileInfo], edges: list[ImportEdge]) -> list[str]:
    code_files = [
        item
        for item in file_infos
        if item.language in {"python", "javascript", "typescript"}
    ]
    by_path = {item.path: item for item in code_files}
    inbound = Counter(edge.to_path for edge in edges)
    largest = sorted(
        code_files,
        key=lambda item: (-item.size, item.path),
    )[:5]
    popular_paths = [
        path
        for path, _count in sorted(
            inbound.items(), key=lambda item: (-item[1], item[0])
        )
    ][:5]
    rows: list[str] = []
    seen: set[str] = set()
    for item in largest:
        if item.path in seen:
            continue
        seen.add(item.path)
        rows.append(
            f"`{item.path}` — {item.size} B, {item.symbols_count} symbols, inbound imports: {inbound.get(item.path, 0)}"
        )
    for path in popular_paths:
        if path in seen or path not in by_path:
            continue
        seen.add(path)
        item = by_path[path]
        rows.append(
            f"`{item.path}` — {item.size} B, {item.symbols_count} symbols, inbound imports: {inbound.get(item.path, 0)}"
        )
    return rows[:8]


def _render_repomap(
    *,
    root: Path,
    stack: str,
    top_level: list[str],
    entrypoints: list[RepoEntrypoint],
    key_modules: list[str],
) -> str:
    lines = [
        "# Repo Map (AI)",
        "",
        "<!-- AGENTSGEN:START section=repomap -->",
        f"- Repo: `{root.resolve().name}`",
        f"- Detected stack: `{stack}`",
        "",
        "## Top-level structure",
    ]
    if top_level:
        lines.extend([f"- {item}" for item in top_level])
    else:
        lines.append("- (no top-level files detected)")
    lines.extend(["", "## Entrypoints guess"])
    if entrypoints:
        lines.extend(
            [
                f"- `{entry.label}`: `{entry.command}` ({entry.source})"
                for entry in entrypoints[:10]
            ]
        )
    else:
        lines.append("- (no conservative entrypoints detected)")
    lines.extend(["", "## Key modules"])
    if key_modules:
        lines.extend([f"- {item}" for item in key_modules])
    else:
        lines.append("- (no code modules detected)")
    lines.extend(["<!-- AGENTSGEN:END section=repomap -->", ""])
    return "\n".join(lines)


def _render_compact_repomap(
    *,
    root: Path,
    stack: str,
    budget_tokens: int,
    top_level: list[str],
    entrypoints: list[RepoEntrypoint],
    ranked: list[RelevanceItem],
    changed_files: list[str],
) -> str:
    lines = [
        "# Repo Map (Compact)",
        "",
        "<!-- AGENTSGEN:START section=repomap_compact -->",
        f"- Repo: `{root.resolve().name}`",
        f"- Detected stack: `{stack}`",
        f"- Budget: `~{budget_tokens}` tokens",
        f"- Changed files detected: `{len(changed_files)}`",
        "",
        "## Priority files",
    ]
    for item in ranked:
        if item.score <= 0:
            continue
        signals = ", ".join(item.signals[:5]) or "baseline"
        lines.append(f"- `{item.path}` — score {item.score}; {signals}")
    if lines[-1] == "## Priority files":
        lines.append("- (no ranked code files detected)")

    lines.extend(["", "## Entrypoints"])
    if entrypoints:
        for entry in entrypoints[:6]:
            lines.append(f"- `{entry.label}` -> `{entry.command}`")
    else:
        lines.append("- (no conservative entrypoints detected)")

    lines.extend(["", "## Top-level"])
    if top_level:
        for item in top_level[:10]:
            lines.append(f"- {item}")
    else:
        lines.append("- (no top-level files detected)")

    lines.append("<!-- AGENTSGEN:END section=repomap_compact -->")
    lines.append("")

    budget = max(budget_tokens, 256)
    kept: list[str] = []
    used_tokens = 0
    for line in lines:
        estimated = _estimate_tokens(line + "\n")
        if kept and used_tokens + estimated > budget:
            break
        kept.append(line)
        used_tokens += estimated
    if kept and kept[-1] != "<!-- AGENTSGEN:END section=repomap_compact -->":
        if "<!-- AGENTSGEN:END section=repomap_compact -->" in lines:
            if kept and kept[-1] == "":
                kept.pop()
            kept.append("<!-- AGENTSGEN:END section=repomap_compact -->")
            kept.append("")
    return "\n".join(kept)


def _select_graph_nodes(
    file_infos: list[RepoFileInfo],
    edges: list[ImportEdge],
    *,
    stack: str,
) -> tuple[list[RepoFileInfo], list[ImportEdge]]:
    inbound = Counter(edge.to_path for edge in edges)
    file_by_path = {
        item.path: item
        for item in file_infos
        if item.language in {"python", "javascript", "typescript"}
    }
    limit = 20 if stack == "mixed" else 30
    ranked = sorted(
        file_by_path.values(),
        key=lambda item: (-inbound.get(item.path, 0), -item.size, item.path),
    )[:limit]
    allowed = {item.path for item in ranked}
    compact_edges = [
        edge for edge in edges if edge.from_path in allowed and edge.to_path in allowed
    ]
    edge_limit = 30 if stack == "mixed" else 60
    return ranked, compact_edges[:edge_limit]


def _mermaid_node_id(path: str) -> str:
    return "n_" + re.sub(r"[^A-Za-z0-9_]", "_", path)


def _render_graph_mmd(nodes: list[RepoFileInfo], edges: list[ImportEdge]) -> str:
    lines = [_MERMAID_START, "graph TD"]
    if not nodes:
        lines.append('  n_empty["(no code files detected)"]')
    else:
        for node in sorted(nodes, key=lambda item: item.path):
            lines.append(f'  {_mermaid_node_id(node.path)}["{node.path}"]')
        for edge in sorted(edges, key=lambda item: (item.from_path, item.to_path)):
            lines.append(
                f"  {_mermaid_node_id(edge.from_path)} --> {_mermaid_node_id(edge.to_path)}"
            )
    lines.append(_MERMAID_END)
    lines.append("")
    return "\n".join(lines)


def _write_or_diff_raw(path: Path, new_content: str, dry_run: bool) -> tuple[bool, str]:
    if path.exists():
        old = read_text(path)
        old_n = normalize_markdown(old)
        new_n = normalize_markdown(new_content)
        if old_n == new_n:
            return False, ""
        if dry_run:
            return True, _unified_diff(path, old_n, new_n)
        write_text_atomic(path, new_n)
        return True, ""
    if dry_run:
        return True, _unified_diff(path, "", new_content)
    write_text_atomic(path, normalize_markdown(new_content))
    return True, ""


def _handle_mermaid_file(
    path: Path, generated_full: str, *, dry_run: bool
) -> FileResult:
    if not path.exists():
        changed, diff = _write_or_diff_raw(path, generated_full, dry_run=dry_run)
        return FileResult(
            path=path, action="created", message="created", changed=changed, diff=diff
        )

    existing = read_text(path)
    if _MERMAID_START not in existing or _MERMAID_END not in existing:
        gen_path = _generated_sibling_path(path)
        changed, diff = _write_or_diff_raw(gen_path, generated_full, dry_run=dry_run)
        return FileResult(
            path=gen_path,
            action="generated",
            message=f"{path.name} has no markers; wrote {gen_path.name} instead",
            changed=changed,
            diff=diff,
        )

    start = existing.index(_MERMAID_START)
    end = existing.index(_MERMAID_END) + len(_MERMAID_END)
    patched = (
        existing[:start]
        + generated_full[: generated_full.index(_MERMAID_END) + len(_MERMAID_END)]
        + existing[end:]
    )
    problems = validate_markers(
        existing.replace(
            _MERMAID_START, "<!-- AGENTSGEN:START section=graph -->"
        ).replace(_MERMAID_END, "<!-- AGENTSGEN:END section=graph -->")
    )
    if problems:
        return FileResult(path=path, action="error", message="invalid graph markers")
    changed, diff = _write_or_diff_raw(path, patched, dry_run=dry_run)
    return FileResult(
        path=path,
        action="updated" if changed else "skipped",
        message="updated" if changed else "no changes",
        changed=changed,
        diff=diff,
    )


def _handle_knowledge_json_file(
    path: Path, generated_full: str, *, dry_run: bool
) -> FileResult:
    if not path.exists():
        changed, diff = _write_or_diff_raw(path, generated_full, dry_run=dry_run)
        return FileResult(
            path=path, action="created", message="created", changed=changed, diff=diff
        )

    existing = read_text(path)
    try:
        parsed = json.loads(existing)
    except Exception:
        parsed = None

    if (
        isinstance(parsed, dict)
        and int(parsed.get("version", 0) or 0) == 1
        and all(
            key in parsed
            for key in ("repo_path", "generated_at", "files", "edges", "entrypoints")
        )
    ):
        changed, diff = _write_or_diff_raw(path, generated_full, dry_run=dry_run)
        return FileResult(
            path=path,
            action="updated" if changed else "skipped",
            message="updated" if changed else "no changes",
            changed=changed,
            diff=diff,
        )

    gen_path = _generated_sibling_path(path)
    changed, diff = _write_or_diff_raw(gen_path, generated_full, dry_run=dry_run)
    return FileResult(
        path=gen_path,
        action="generated",
        message=f"{path.name} has no markers; wrote {gen_path.name} instead",
        changed=changed,
        diff=diff,
    )


def _repo_files(root: Path, output_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if _should_skip(path, root, output_dir):
            continue
        if (
            path.name not in _TEXT_FILENAMES
            and path.suffix.lower() not in set(_LANGUAGE_BY_SUFFIX) | _CODE_EXTENSIONS
        ):
            continue
        files.append(path)
    return sorted(files, key=lambda item: _rel(item, root))


def build_understanding_payload(
    root: Path,
    *,
    output_dir: Path,
    compact_budget_tokens: int = 4000,
) -> dict[str, object]:
    det = detect_repo(root)
    stack = (
        str(det.project.get("primary_stack", "") or "unknown").strip().lower()
        or "unknown"
    )
    files = _repo_files(root, output_dir)
    source_roots = _source_roots(root, det.paths)
    file_infos, edges = _scan_imports(files, root=root, source_roots=source_roots)
    top_level = _top_level_structure(root)
    entrypoints = _detect_entrypoints(root)
    key_modules = _key_modules(file_infos, edges)
    ranked, changed_files, entrypoint_files = _rank_relevance(
        root=root,
        file_infos=file_infos,
        edges=edges,
        entrypoints=entrypoints,
    )
    graph_nodes, graph_edges = _select_graph_nodes(file_infos, edges, stack=stack)

    repomap = _render_repomap(
        root=root,
        stack=stack,
        top_level=top_level,
        entrypoints=entrypoints,
        key_modules=key_modules,
    )
    compact_repomap = _render_compact_repomap(
        root=root,
        stack=stack,
        budget_tokens=compact_budget_tokens,
        top_level=top_level,
        entrypoints=entrypoints,
        ranked=ranked[:16],
        changed_files=changed_files,
    )
    graph = _render_graph_mmd(graph_nodes, graph_edges)
    knowledge = {
        "version": 1,
        "repo_path": ".",
        "generated_at": "",
        "files": [
            {
                "path": item.path,
                "size": item.size,
                "language": item.language,
                "symbols_count": item.symbols_count,
            }
            for item in file_infos
        ],
        "edges": [
            {"from": edge.from_path, "to": edge.to_path, "kind": edge.kind}
            for edge in edges
        ],
        "entrypoints": [
            {"label": item.label, "command": item.command, "source": item.source}
            for item in entrypoints
        ],
        "changed_files": changed_files,
        "entrypoint_files": entrypoint_files,
        "relevance": [
            {
                "path": item.path,
                "score": item.score,
                "signals": list(item.signals),
                "distance_from_entrypoint": item.distance_from_entrypoint,
                "changed": item.changed,
                "entrypoint": item.entrypoint,
            }
            for item in ranked[:20]
        ],
    }
    existing_knowledge = root / "agents.knowledge.json"
    if existing_knowledge.exists():
        try:
            existing_payload = json.loads(
                existing_knowledge.read_text(encoding="utf-8")
            )
        except Exception:
            existing_payload = None
        if isinstance(existing_payload, dict) and _stable_knowledge_payload(
            existing_payload
        ) == _stable_knowledge_payload(knowledge):
            knowledge["generated_at"] = str(
                existing_payload.get("generated_at", "") or ""
            )
        else:
            knowledge["generated_at"] = _utc_now_iso()
    else:
        knowledge["generated_at"] = _utc_now_iso()
    return {
        "stack": stack,
        "repomap": repomap,
        "compact_repomap": compact_repomap,
        "graph": graph,
        "knowledge": knowledge,
        "summary": {
            "files_count": len(file_infos),
            "edges_count": len(edges),
            "entrypoints_count": len(entrypoints),
            "changed_files_count": len(changed_files),
            "compact_budget_tokens": compact_budget_tokens,
        },
    }


def apply_understanding(
    root: Path,
    *,
    output_dir: Path,
    compact_budget_tokens: int = 4000,
    dry_run: bool = False,
) -> tuple[list[FileResult], dict[str, object]]:
    payload = build_understanding_payload(
        root,
        output_dir=output_dir,
        compact_budget_tokens=compact_budget_tokens,
    )
    repomap_path = output_dir / "repomap.md"
    compact_repomap_path = output_dir / "repomap.compact.md"
    graph_path = output_dir / "graph.mmd"
    knowledge_path = root / "agents.knowledge.json"
    results = [
        _handle_file(
            repomap_path,
            payload["repomap"],
            required=["repomap"],
            dry_run=dry_run,
            print_diff=False,
        ),
        _handle_file(
            compact_repomap_path,
            payload["compact_repomap"],
            required=["repomap_compact"],
            dry_run=dry_run,
            print_diff=False,
        ),
        _handle_mermaid_file(graph_path, payload["graph"], dry_run=dry_run),
        _handle_knowledge_json_file(
            knowledge_path,
            json.dumps(payload["knowledge"], indent=2) + "\n",
            dry_run=dry_run,
        ),
    ]
    return results, payload
