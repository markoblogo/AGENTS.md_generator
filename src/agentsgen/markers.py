from __future__ import annotations

import re
from dataclasses import dataclass

from .constants import MARKER_PREFIX


@dataclass(frozen=True)
class MarkerRange:
    section: str
    start_marker_idx: int
    end_marker_idx: int  # start index of END marker
    content_start: int
    content_end: int


# Accept both legacy and new marker formats:
# - <!-- AGENTSGEN:START commands -->
# - <!-- AGENTSGEN:START section=commands -->
_START_RE = re.compile(
    r"<!--\s*"
    + re.escape(MARKER_PREFIX)
    + r":START\s+(?:section=)?([a-zA-Z0-9_\-]+)\s*-->"
)
_END_RE = re.compile(
    r"<!--\s*"
    + re.escape(MARKER_PREFIX)
    + r":END\s+(?:section=)?([a-zA-Z0-9_\-]+)\s*-->"
)


def has_any_agentsgen_markers(text: str) -> bool:
    return f"<!-- {MARKER_PREFIX}:START" in text and f"<!-- {MARKER_PREFIX}:END" in text


def count_agentsgen_marker_sections(text: str) -> int:
    return sum(1 for _ in _START_RE.finditer(text))


@dataclass(frozen=True)
class MarkerProblem:
    kind: str
    message: str


def validate_markers(text: str) -> list[MarkerProblem]:
    """Validate that markers are:

    - properly nested (no nested blocks)
    - have matching START/END names
    - section names are unique (no duplicates)
    """

    problems: list[MarkerProblem] = []
    seen_start: set[str] = set()

    # Scan in order of appearance.
    tokens: list[tuple[int, str, str]] = []
    for m in _START_RE.finditer(text):
        tokens.append((m.start(), "start", m.group(1)))
    for m in _END_RE.finditer(text):
        tokens.append((m.start(), "end", m.group(1)))
    tokens.sort(key=lambda t: t[0])

    stack: list[str] = []
    for _, ttype, section in tokens:
        if ttype == "start":
            if stack:
                problems.append(
                    MarkerProblem(
                        kind="nested",
                        message=f"Nested START marker '{section}' inside '{stack[-1]}' is not allowed.",
                    )
                )
            if section in seen_start:
                problems.append(
                    MarkerProblem(
                        kind="duplicate",
                        message=f"Duplicate START marker for section '{section}' found.",
                    )
                )
            seen_start.add(section)
            stack.append(section)
        else:
            if not stack:
                problems.append(
                    MarkerProblem(
                        kind="unmatched_end",
                        message=f"END marker for section '{section}' has no matching START.",
                    )
                )
                continue
            open_sec = stack.pop()
            if open_sec != section:
                problems.append(
                    MarkerProblem(
                        kind="mismatch",
                        message=f"Marker mismatch: START '{open_sec}' closed by END '{section}'.",
                    )
                )

    if stack:
        for open_sec in reversed(stack):
            problems.append(
                MarkerProblem(
                    kind="unclosed",
                    message=f"START marker for section '{open_sec}' has no matching END.",
                )
            )

    return problems


def find_section_range(text: str, section: str) -> MarkerRange | None:
    # Use regex scanning so we accept both legacy and new marker formats.
    start_m = None
    for m in _START_RE.finditer(text):
        if m.group(1) == section:
            start_m = m
            break
    if start_m is None:
        return None

    end_m = None
    for m in _END_RE.finditer(text, start_m.end()):
        if m.group(1) == section:
            end_m = m
            break
    if end_m is None:
        return None

    content_start = start_m.end()
    if content_start < len(text) and text[content_start : content_start + 1] == "\n":
        content_start += 1

    content_end = end_m.start()
    if content_end > 0 and text[content_end - 1 : content_end] == "\n":
        content_end -= 1

    return MarkerRange(
        section=section,
        start_marker_idx=start_m.start(),
        end_marker_idx=end_m.start(),
        content_start=content_start,
        content_end=content_end,
    )


def extract_section_content(text: str, section: str) -> str | None:
    r = find_section_range(text, section)
    if r is None:
        return None
    return text[r.content_start : r.content_end]


def replace_section_content(
    text: str, section: str, new_content: str
) -> tuple[str, bool]:
    r = find_section_range(text, section)
    if r is None:
        return text, False

    body = new_content.strip("\n")
    # Rebuild only the inner range; keep markers and surrounding untouched.
    out = text[: r.content_start] + body + text[r.content_end :]
    return out, True
