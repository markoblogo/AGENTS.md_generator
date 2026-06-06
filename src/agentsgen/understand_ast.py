from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from .io_utils import read_text

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


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def should_skip(path: Path, root: Path, output_dir: Path) -> bool:
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


def language_for_path(path: Path) -> str:
    return _LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "unknown")


def count_symbols(path: Path, text: str) -> int:
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


def source_roots(root: Path, detected_paths: dict[str, object]) -> list[Path]:
    roots: list[Path] = []
    for raw in list(detected_paths.get("source_dirs", []) or []):
        candidate = (root / str(raw)).resolve()
        if candidate.exists():
            roots.append(candidate)
    if not roots:
        roots.append(root.resolve())
    return roots


def python_module_candidates(
    path: Path, root: Path, source_roots: list[Path]
) -> list[str]:
    candidates: list[str] = []
    for source_root in source_roots:
        try:
            rel_path = path.resolve().relative_to(source_root.resolve())
        except ValueError:
            continue
        parts = list(rel_path.parts)
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
        rel_path = path.resolve().relative_to(root.resolve())
        parts = list(rel_path.parts)
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


def build_python_module_map(
    files: list[Path], root: Path, source_roots: list[Path]
) -> dict[str, str]:
    module_map: dict[str, str] = {}
    for path in files:
        if path.suffix != ".py":
            continue
        file_path = rel(path, root)
        for candidate in python_module_candidates(path, root, source_roots):
            module_map[candidate] = file_path
    return module_map


def resolve_python_import(
    current_path: Path,
    module_map: dict[str, str],
    root: Path,
    source_roots: list[Path],
    module: str | None,
    level: int,
) -> str | None:
    current_candidates = python_module_candidates(current_path, root, source_roots)
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


def resolve_js_import(current_path: Path, target_spec: str, root: Path) -> str | None:
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
                return rel(candidate, root)
            except ValueError:
                return None
    return None


def scan_imports(
    files: list[Path],
    *,
    root: Path,
    source_roots: list[Path],
) -> tuple[list[RepoFileInfo], list[ImportEdge]]:
    file_infos: list[RepoFileInfo] = []
    edges: list[ImportEdge] = []
    python_module_map = build_python_module_map(files, root, source_roots)

    for path in sorted(files, key=lambda item: rel(item, root)):
        text = read_text(path)
        rel_path = rel(path, root)
        file_infos.append(
            RepoFileInfo(
                path=rel_path,
                size=path.stat().st_size,
                language=language_for_path(path),
                symbols_count=count_symbols(path, text),
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
                        target_rel = resolve_python_import(
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
                    target_rel = resolve_python_import(
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
                target_rel = resolve_js_import(path, spec, root)
                if target_rel and target_rel not in seen_targets:
                    seen_targets.add(target_rel)
                    edges.append(ImportEdge(rel_path, target_rel))

    deduped = sorted(
        {(edge.from_path, edge.to_path, edge.kind) for edge in edges},
        key=lambda item: (item[0], item[1], item[2]),
    )
    return file_infos, [ImportEdge(*edge) for edge in deduped]


def repo_files(root: Path, output_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if should_skip(path, root, output_dir):
            continue
        if (
            path.name not in _TEXT_FILENAMES
            and path.suffix.lower() not in set(_LANGUAGE_BY_SUFFIX) | _CODE_EXTENSIONS
        ):
            continue
        files.append(path)
    return sorted(files, key=lambda item: rel(item, root))
