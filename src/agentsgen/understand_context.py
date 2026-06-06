from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .detect import detect_repo
from .io_utils import read_text, write_text_atomic
from .markers import validate_markers
from .normalize import normalize_markdown
from .patch_engine import generated_sibling_path, handle_file, unified_diff
from .result_types import FileResult
from .understand_ast import (
    ImportEdge,
    RepoFileInfo,
    _EXCLUDED_DIRS,
    _VISIBLE_HIDDEN_NAMES,
    rel,
    repo_files,
    scan_imports,
    source_roots,
)
from .validators import validate_knowledge_payload

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


_MAKE_TARGET_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*):")
_MERMAID_START = "%% AGENTSGEN:START section=graph"
_MERMAID_END = "%% AGENTSGEN:END section=graph"


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


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def stable_knowledge_payload(payload: dict[str, object]) -> str:
    clone = json.loads(json.dumps(payload))
    clone["generated_at"] = ""
    return json.dumps(clone, sort_keys=True, separators=(",", ":"))


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def top_level_structure(root: Path) -> list[str]:
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


def entrypoints_from_config(root: Path) -> list[RepoEntrypoint]:
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


def entrypoints_from_package_json(root: Path) -> list[RepoEntrypoint]:
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


def entrypoints_from_makefile(root: Path) -> list[RepoEntrypoint]:
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


def entrypoints_from_pyproject(root: Path) -> list[RepoEntrypoint]:
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
    return [
        RepoEntrypoint(label=str(label), command=str(label), source="pyproject")
        for label in sorted(scripts)
    ]


def detect_entrypoints(root: Path) -> list[RepoEntrypoint]:
    rows = entrypoints_from_config(root)
    if rows:
        return rows
    rows = entrypoints_from_package_json(root)
    if rows:
        return rows
    rows = entrypoints_from_makefile(root)
    if rows:
        return rows
    return entrypoints_from_pyproject(root)


def git_changed_files(root: Path) -> list[str]:
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


def extract_command_file_hints(command: str, root: Path) -> list[str]:
    hints: list[str] = []
    for token in re.findall(r"[A-Za-z0-9_./-]+\.[A-Za-z0-9]+", command):
        candidate = (root / token).resolve()
        if candidate.exists() and candidate.is_file():
            try:
                hints.append(rel(candidate, root))
            except ValueError:
                continue
    return sorted(set(hints))


def default_entry_file_hints(file_infos: list[RepoFileInfo]) -> list[str]:
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


def entrypoint_files(
    *,
    root: Path,
    file_infos: list[RepoFileInfo],
    entrypoints: list[RepoEntrypoint],
) -> list[str]:
    available = {item.path for item in file_infos}
    rows: list[str] = []
    for entry in entrypoints:
        rows.extend(extract_command_file_hints(entry.command, root))
    if rows:
        return sorted({path for path in rows if path in available})
    return default_entry_file_hints(file_infos)


def rank_relevance(
    *,
    root: Path,
    file_infos: list[RepoFileInfo],
    edges: list[ImportEdge],
    entrypoints: list[RepoEntrypoint],
) -> tuple[list[RelevanceItem], list[str], list[str]]:
    changed_files = git_changed_files(root)
    changed_set = set(changed_files)
    entrypoint_file_list = entrypoint_files(
        root=root, file_infos=file_infos, entrypoints=entrypoints
    )
    entrypoint_set = set(entrypoint_file_list)
    inbound = Counter(edge.to_path for edge in edges)
    outbound = Counter(edge.from_path for edge in edges)
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.from_path, []).append(edge.to_path)

    distances: dict[str, int] = {}
    queue = list(entrypoint_file_list)
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
    return ranked, changed_files, entrypoint_file_list


def focus_matches(
    *,
    root: Path,
    file_infos: list[RepoFileInfo],
    query: str,
) -> set[str]:
    needle = query.strip().lower()
    if not needle:
        return set()
    matches: set[str] = set()
    for item in file_infos:
        if needle in item.path.lower():
            matches.add(item.path)
            continue
        file_path = root / item.path
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if needle in content.lower():
            matches.add(item.path)
    return matches


def related_paths(
    *,
    seeds: set[str],
    edges: list[ImportEdge],
) -> set[str]:
    if not seeds:
        return set()
    related = set(seeds)
    for edge in edges:
        if edge.from_path in seeds:
            related.add(edge.to_path)
        if edge.to_path in seeds:
            related.add(edge.from_path)
    return related


def slice_relevance(
    *,
    root: Path,
    file_infos: list[RepoFileInfo],
    edges: list[ImportEdge],
    ranked: list[RelevanceItem],
    focus: str | None,
    changed_only: bool,
) -> tuple[list[RelevanceItem], dict[str, object]]:
    focus_query = (focus or "").strip()
    matches = focus_matches(root=root, file_infos=file_infos, query=focus_query)
    changed_matches = {item.path for item in ranked if item.changed}

    allowed: set[str] | None = None
    focus_related: set[str] = set()
    changed_related: set[str] = set()

    if focus_query:
        focus_related = related_paths(seeds=matches, edges=edges)
        allowed = set(focus_related)
    if changed_only:
        changed_related = related_paths(seeds=changed_matches, edges=edges)
        allowed = set(changed_related) if allowed is None else allowed & changed_related

    rows: list[RelevanceItem] = []
    source_rows = (
        ranked if allowed is None else [item for item in ranked if item.path in allowed]
    )
    for item in source_rows:
        score = item.score
        signals = list(item.signals)
        if focus_query:
            if item.path in matches:
                score += 40
                signals.insert(0, f"focus:{focus_query}")
            elif item.path in focus_related:
                score += 12
                signals.insert(0, "focus-neighbor")
        if changed_only:
            if item.changed:
                score += 18
                if "git-changed" not in signals:
                    signals.insert(0, "git-changed")
            elif item.path in changed_related:
                score += 6
                signals.insert(0, "changed-neighbor")
        rows.append(
            RelevanceItem(
                path=item.path,
                score=score,
                signals=tuple(dict.fromkeys(signals)),
                distance_from_entrypoint=item.distance_from_entrypoint,
                changed=item.changed,
                entrypoint=item.entrypoint,
            )
        )

    sliced = sorted(rows, key=lambda item: (-item.score, item.path))
    return sliced, {
        "focus": focus_query or None,
        "focus_matches": sorted(matches),
        "changed_only": changed_only,
        "changed_matches": sorted(changed_matches),
    }


def key_modules(file_infos: list[RepoFileInfo], edges: list[ImportEdge]) -> list[str]:
    code_files = [
        item
        for item in file_infos
        if item.language in {"python", "javascript", "typescript"}
    ]
    by_path = {item.path: item for item in code_files}
    inbound = Counter(edge.to_path for edge in edges)
    largest = sorted(code_files, key=lambda item: (-item.size, item.path))[:5]
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


def render_repomap(
    *,
    root: Path,
    stack: str,
    top_level: list[str],
    entrypoints: list[RepoEntrypoint],
    key_module_rows: list[str],
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
    if key_module_rows:
        lines.extend([f"- {item}" for item in key_module_rows])
    else:
        lines.append("- (no code modules detected)")
    lines.extend(["<!-- AGENTSGEN:END section=repomap -->", ""])
    return "\n".join(lines)


def render_compact_repomap(
    *,
    root: Path,
    stack: str,
    budget_tokens: int,
    top_level: list[str],
    entrypoints: list[RepoEntrypoint],
    ranked: list[RelevanceItem],
    changed_files: list[str],
    focus: str | None,
    changed_only: bool,
) -> str:
    lines = [
        "# Repo Map (Compact)",
        "",
        "<!-- AGENTSGEN:START section=repomap_compact -->",
        f"- Repo: `{root.resolve().name}`",
        f"- Detected stack: `{stack}`",
        f"- Budget: `~{budget_tokens}` tokens",
        f"- Changed files detected: `{len(changed_files)}`",
        f"- Mode: `{'changed' if changed_only else 'full'}`",
        "",
        "## Priority files",
    ]
    if focus:
        lines.insert(7, f"- Focus: `{focus}`")
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
        estimated = estimate_tokens(line + "\n")
        if kept and used_tokens + estimated > budget:
            break
        kept.append(line)
        used_tokens += estimated
    end_marker = "<!-- AGENTSGEN:END section=repomap_compact -->"
    if kept and end_marker not in kept and end_marker in lines:
        if kept and kept[-1] == "":
            kept.pop()
        kept.append(end_marker)
        kept.append("")
    return "\n".join(kept)


def select_graph_nodes(
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


def mermaid_node_id(path: str) -> str:
    return "n_" + re.sub(r"[^A-Za-z0-9_]", "_", path)


def render_graph_mmd(nodes: list[RepoFileInfo], edges: list[ImportEdge]) -> str:
    lines = [_MERMAID_START, "graph TD"]
    if not nodes:
        lines.append('  n_empty["(no code files detected)"]')
    else:
        for node in sorted(nodes, key=lambda item: item.path):
            lines.append(f'  {mermaid_node_id(node.path)}["{node.path}"]')
        for edge in sorted(edges, key=lambda item: (item.from_path, item.to_path)):
            lines.append(
                f"  {mermaid_node_id(edge.from_path)} --> {mermaid_node_id(edge.to_path)}"
            )
    lines.append(_MERMAID_END)
    lines.append("")
    return "\n".join(lines)


def write_or_diff_raw(path: Path, new_content: str, dry_run: bool) -> tuple[bool, str]:
    if path.exists():
        old = read_text(path)
        old_n = normalize_markdown(old)
        new_n = normalize_markdown(new_content)
        if old_n == new_n:
            return False, ""
        if dry_run:
            return True, unified_diff(path, old_n, new_n)
        write_text_atomic(path, new_n)
        return True, ""
    if dry_run:
        return True, unified_diff(path, "", new_content)
    write_text_atomic(path, normalize_markdown(new_content))
    return True, ""


def handle_mermaid_file(path: Path, generated_full: str, *, dry_run: bool) -> FileResult:
    if not path.exists():
        changed, diff = write_or_diff_raw(path, generated_full, dry_run=dry_run)
        return FileResult(
            path=path, action="created", message="created", changed=changed, diff=diff
        )

    existing = read_text(path)
    if _MERMAID_START not in existing or _MERMAID_END not in existing:
        gen_path = generated_sibling_path(path)
        changed, diff = write_or_diff_raw(gen_path, generated_full, dry_run=dry_run)
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
    changed, diff = write_or_diff_raw(path, patched, dry_run=dry_run)
    return FileResult(
        path=path,
        action="updated" if changed else "skipped",
        message="updated" if changed else "no changes",
        changed=changed,
        diff=diff,
    )


def handle_knowledge_json_file(
    path: Path, generated_full: str, *, dry_run: bool
) -> FileResult:
    if not path.exists():
        changed, diff = write_or_diff_raw(path, generated_full, dry_run=dry_run)
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
        changed, diff = write_or_diff_raw(path, generated_full, dry_run=dry_run)
        return FileResult(
            path=path,
            action="updated" if changed else "skipped",
            message="updated" if changed else "no changes",
            changed=changed,
            diff=diff,
        )

    gen_path = generated_sibling_path(path)
    changed, diff = write_or_diff_raw(gen_path, generated_full, dry_run=dry_run)
    return FileResult(
        path=gen_path,
        action="generated",
        message=f"{path.name} has no markers; wrote {gen_path.name} instead",
        changed=changed,
        diff=diff,
    )


def build_understanding_payload(
    root: Path,
    *,
    output_dir: Path,
    compact_budget_tokens: int = 4000,
    focus: str | None = None,
    changed_only: bool = False,
) -> dict[str, object]:
    det = detect_repo(root)
    stack = (
        str(det.project.get("primary_stack", "") or "unknown").strip().lower()
        or "unknown"
    )
    files = repo_files(root, output_dir)
    roots = source_roots(root, det.paths)
    file_infos, edges = scan_imports(files, root=root, source_roots=roots)
    top_level = top_level_structure(root)
    entrypoints = detect_entrypoints(root)
    key_module_rows = key_modules(file_infos, edges)
    ranked, changed_files, entrypoint_file_list = rank_relevance(
        root=root,
        file_infos=file_infos,
        edges=edges,
        entrypoints=entrypoints,
    )
    ranked, slice_meta = slice_relevance(
        root=root,
        file_infos=file_infos,
        edges=edges,
        ranked=ranked,
        focus=focus,
        changed_only=changed_only,
    )
    graph_nodes, graph_edges = select_graph_nodes(file_infos, edges, stack=stack)

    repomap = render_repomap(
        root=root,
        stack=stack,
        top_level=top_level,
        entrypoints=entrypoints,
        key_module_rows=key_module_rows,
    )
    compact_repomap = render_compact_repomap(
        root=root,
        stack=stack,
        budget_tokens=compact_budget_tokens,
        top_level=top_level,
        entrypoints=entrypoints,
        ranked=ranked[:16],
        changed_files=changed_files,
        focus=slice_meta["focus"],
        changed_only=changed_only,
    )
    graph = render_graph_mmd(graph_nodes, graph_edges)
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
        "entrypoint_files": entrypoint_file_list,
        "slice": slice_meta,
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
        if isinstance(existing_payload, dict) and stable_knowledge_payload(
            existing_payload
        ) == stable_knowledge_payload(knowledge):
            knowledge["generated_at"] = str(
                existing_payload.get("generated_at", "") or ""
            )
        else:
            knowledge["generated_at"] = utc_now_iso()
    else:
        knowledge["generated_at"] = utc_now_iso()
    validate_knowledge_payload(knowledge)
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
            "focus": slice_meta["focus"],
            "changed_only": changed_only,
            "slice_files_count": len(ranked),
        },
    }


def apply_understanding(
    root: Path,
    *,
    output_dir: Path,
    compact_budget_tokens: int = 4000,
    focus: str | None = None,
    changed_only: bool = False,
    dry_run: bool = False,
) -> tuple[list[FileResult], dict[str, object]]:
    payload = build_understanding_payload(
        root,
        output_dir=output_dir,
        compact_budget_tokens=compact_budget_tokens,
        focus=focus,
        changed_only=changed_only,
    )
    repomap_path = output_dir / "repomap.md"
    compact_repomap_path = output_dir / "repomap.compact.md"
    graph_path = output_dir / "graph.mmd"
    knowledge_path = root / "agents.knowledge.json"
    results = [
        handle_file(
            repomap_path,
            payload["repomap"],
            required=["repomap"],
            dry_run=dry_run,
            print_diff=False,
        ),
        handle_file(
            compact_repomap_path,
            payload["compact_repomap"],
            required=["repomap_compact"],
            dry_run=dry_run,
            print_diff=False,
        ),
        handle_mermaid_file(graph_path, payload["graph"], dry_run=dry_run),
        handle_knowledge_json_file(
            knowledge_path,
            json.dumps(payload["knowledge"], indent=2) + "\n",
            dry_run=dry_run,
        ),
    ]
    return results, payload
