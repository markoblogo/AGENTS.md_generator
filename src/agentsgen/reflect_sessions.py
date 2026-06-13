from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from .generated_artifacts import handle_generated_json_artifact
from .io_utils import read_text
from .patch_engine import generated_sibling_path, write_or_diff
from .result_types import FileResult
from .validators import (
    validate_reflect_sessions_payload,
    validate_reflect_signals_payload,
)


SHORT_PROMPT_WORD_LIMIT = 8
SHORT_PROMPT_CHAR_LIMIT = 80
LONG_SESSION_MINUTES = 30
REDIRECT_PATTERN = re.compile(
    r"\b(instead|don't|do not|stop|change|redo|not this|use this|wait)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SessionSummary:
    session_id: str
    tool: str
    originator: str
    source: str
    cwd: str
    started_at: str
    last_event_at: str
    duration_minutes: int
    user_messages: int
    prompt_chars: int
    prompt_words: int
    plan_first: bool
    redirects: int
    long_session: bool
    short_prompts: tuple[str, ...]


@dataclass(frozen=True)
class SessionTranscript:
    summary: SessionSummary
    user_messages: tuple[str, ...]


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _parse_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_session_for_target(cwd: str, target: Path) -> bool:
    try:
        cwd_path = Path(cwd).resolve()
        target_path = target.resolve()
    except Exception:
        return False
    return cwd_path == target_path or target_path in cwd_path.parents


def _iter_session_files(codex_root: Path) -> list[Path]:
    if not codex_root.exists():
        return []
    return sorted(codex_root.rglob("*.jsonl"))


def _extract_short_prompt(text: str) -> str | None:
    stripped = " ".join(text.split())
    if not stripped:
        return None
    if len(stripped) > SHORT_PROMPT_CHAR_LIMIT:
        return None
    if len(stripped.split()) > SHORT_PROMPT_WORD_LIMIT:
        return None
    return stripped


def _plan_first(text: str) -> bool:
    lowered = text.lower()
    return "plan" in lowered or "proposal" in lowered or "first " in lowered


def _render_patterns(
    summary: dict[str, object], top_short_prompts: list[dict[str, object]]
) -> str:
    session_count = cast(int, summary["session_count"])
    prompt_count = cast(int, summary["prompt_count"])
    avg_prompt_chars = cast(int, summary["avg_prompt_chars"])
    redirects = cast(int, summary["redirect_count"])
    plan_first_ratio = cast(int, summary["plan_first_ratio"])
    long_sessions = cast(int, summary["long_sessions"])
    top_hours_items = cast(list[dict[str, object]], summary.get("top_hours", []))
    top_hours = [str(cast(int, item["hour"])) for item in top_hours_items]
    most_used = str(top_short_prompts[0]["prompt"]) if top_short_prompts else ""

    lines = [
        "---",
        'generated_by: "agentsgen"',
        'artifact: "agent-patterns"',
        "experimental: true",
        "---",
        "",
        "# Agent Session Retrospective",
        "",
        f"- Sessions analyzed: `{session_count}`",
        f"- User prompts counted: `{prompt_count}`",
        f"- Plan-first ratio: `{plan_first_ratio}%`",
        f"- Redirects detected: `{redirects}`",
        f"- Long sessions (>= {LONG_SESSION_MINUTES}m): `{long_sessions}`",
        "",
        "## Signals",
        "",
    ]
    if avg_prompt_chars <= 60:
        lines.append("- Prompt style: concise")
    elif avg_prompt_chars <= 180:
        lines.append("- Prompt style: mixed")
    else:
        lines.append("- Prompt style: detailed")
    if top_hours:
        lines.append(f"- Peak working hours: `{', '.join(top_hours)}`")
    if most_used:
        lines.append(f"- Most repeated short prompt: `{most_used}`")
    if redirects == 0:
        lines.append("- Steering pattern: low redirect rate")
    else:
        lines.append("- Steering pattern: active mid-task correction")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This is an experimental local-only artifact derived from session transcripts.",
            "- Treat it as operational guidance, not as a behavioral scorecard.",
            "",
        ]
    )
    return "\n".join(lines)


def _handle_generated_text_artifact(
    path: Path,
    content: str,
    *,
    dry_run: bool,
    print_diff: bool,
) -> FileResult:
    generated_marker = 'generated_by: "agentsgen"'
    if not path.exists():
        changed, diff = write_or_diff(
            path, content, dry_run=dry_run, print_diff=print_diff
        )
        return FileResult(
            path=path, action="created", message="created", changed=changed, diff=diff
        )

    existing = read_text(path)
    if generated_marker in existing:
        changed, diff = write_or_diff(
            path, content, dry_run=dry_run, print_diff=print_diff
        )
        return FileResult(
            path=path,
            action="updated" if changed else "skipped",
            message="updated" if changed else "no changes",
            changed=changed,
            diff=diff,
        )

    gen_path = generated_sibling_path(path)
    changed, diff = write_or_diff(
        gen_path, content, dry_run=dry_run, print_diff=print_diff
    )
    return FileResult(
        path=gen_path,
        action="generated",
        message=f"{path.name} is user-managed; wrote generated sibling",
        changed=changed,
        diff=diff,
    )


def _parse_session_transcript(path: Path, target: Path) -> SessionTranscript | None:
    meta: dict[str, object] | None = None
    user_messages: list[tuple[datetime | None, str]] = []
    last_event_at: datetime | None = None

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        timestamp = _parse_timestamp(str(payload.get("timestamp", "") or ""))
        if timestamp and (last_event_at is None or timestamp > last_event_at):
            last_event_at = timestamp
        record_type = str(payload.get("type", "") or "")
        body = payload.get("payload", {})
        if record_type == "session_meta" and isinstance(body, dict):
            meta = body
            continue
        if record_type != "event_msg" or not isinstance(body, dict):
            continue
        if body.get("type") != "user_message":
            continue
        message = str(body.get("message", "") or "").strip()
        if not message:
            continue
        user_messages.append((timestamp, message))

    if not meta:
        return None
    cwd = str(meta.get("cwd", "") or "")
    if not _is_session_for_target(cwd, target):
        return None

    started_at = _parse_timestamp(str(meta.get("timestamp", "") or ""))
    if started_at is None:
        started_at = user_messages[0][0] if user_messages else last_event_at
    if started_at is None:
        return None
    if last_event_at is None:
        last_event_at = started_at

    prompt_chars = sum(len(text) for _, text in user_messages)
    prompt_words = sum(len(text.split()) for _, text in user_messages)
    short_prompts = tuple(
        prompt
        for _, text in user_messages
        if (prompt := _extract_short_prompt(text)) is not None
    )
    redirects = sum(
        1
        for index, (_, text) in enumerate(user_messages)
        if index > 0 and REDIRECT_PATTERN.search(text)
    )
    duration_minutes = max(0, int((last_event_at - started_at).total_seconds() // 60))

    return SessionTranscript(
        summary=SessionSummary(
            session_id=str(meta.get("id", "") or path.stem),
            tool="codex",
            originator=str(meta.get("originator", "") or ""),
            source=str(meta.get("source", "") or ""),
            cwd=cwd,
            started_at=started_at.isoformat().replace("+00:00", "Z"),
            last_event_at=last_event_at.isoformat().replace("+00:00", "Z"),
            duration_minutes=duration_minutes,
            user_messages=len(user_messages),
            prompt_chars=prompt_chars,
            prompt_words=prompt_words,
            plan_first=bool(user_messages and _plan_first(user_messages[0][1])),
            redirects=redirects,
            long_session=duration_minutes >= LONG_SESSION_MINUTES,
            short_prompts=short_prompts,
        ),
        user_messages=tuple(text for _, text in user_messages),
    )


def load_codex_session_transcripts(
    target: Path, codex_root: Path
) -> list[SessionTranscript]:
    session_files = _iter_session_files(codex_root)
    return [
        item
        for path in session_files
        if (item := _parse_session_transcript(path, target))
    ]


def reflect_sessions_payload(
    target: Path, codex_root: Path
) -> tuple[dict[str, object], dict[str, object]]:
    transcripts = load_codex_session_transcripts(target, codex_root)
    sessions = [item.summary for item in transcripts]

    prompt_count = sum(item.user_messages for item in sessions)
    prompt_chars_total = sum(item.prompt_chars for item in sessions)
    plan_first_sessions = sum(1 for item in sessions if item.plan_first)
    redirects = sum(item.redirects for item in sessions)
    long_sessions = sum(1 for item in sessions if item.long_session)
    hour_counts: Counter[int] = Counter()
    short_prompt_counts: Counter[str] = Counter()
    for item in sessions:
        hour = _parse_timestamp(item.started_at)
        if hour is not None:
            hour_counts[hour.hour] += 1
        short_prompt_counts.update(item.short_prompts)

    top_short_prompts = [
        {"prompt": prompt, "count": count}
        for prompt, count in short_prompt_counts.most_common(10)
    ]
    top_hours = [
        {"hour": hour, "count": count} for hour, count in hour_counts.most_common(5)
    ]

    session_payload: dict[str, object] = {
        "version": 1,
        "generated_by": "agentsgen",
        "generated_at": utc_now_iso(),
        "repo": {"path": str(target.resolve())},
        "source": {"tool": "codex", "root": str(codex_root)},
        "sessions": [
            {
                "session_id": item.session_id,
                "tool": item.tool,
                "originator": item.originator,
                "source": item.source,
                "cwd": item.cwd,
                "started_at": item.started_at,
                "last_event_at": item.last_event_at,
                "duration_minutes": item.duration_minutes,
                "user_messages": item.user_messages,
                "prompt_chars": item.prompt_chars,
                "prompt_words": item.prompt_words,
                "plan_first": item.plan_first,
                "redirects": item.redirects,
                "long_session": item.long_session,
                "short_prompts": list(item.short_prompts),
            }
            for item in sessions
        ],
        "summary": {
            "session_count": len(sessions),
            "prompt_count": prompt_count,
            "prompt_chars_total": prompt_chars_total,
            "avg_prompt_chars": int(prompt_chars_total / prompt_count)
            if prompt_count
            else 0,
            "plan_first_sessions": plan_first_sessions,
            "redirect_count": redirects,
            "long_sessions": long_sessions,
        },
    }
    validate_reflect_sessions_payload(session_payload)

    signals_payload: dict[str, object] = {
        "version": 1,
        "generated_by": "agentsgen",
        "generated_at": utc_now_iso(),
        "repo": {"path": str(target.resolve())},
        "source": {"tool": "codex", "root": str(codex_root)},
        "summary": {
            "session_count": len(sessions),
            "prompt_count": prompt_count,
            "avg_prompt_chars": int(prompt_chars_total / prompt_count)
            if prompt_count
            else 0,
            "plan_first_ratio": int((plan_first_sessions * 100) / len(sessions))
            if sessions
            else 0,
            "redirect_count": redirects,
            "long_sessions": long_sessions,
            "top_hours": top_hours,
        },
        "top_short_prompts": top_short_prompts,
    }
    validate_reflect_signals_payload(signals_payload)
    return session_payload, signals_payload


def apply_reflect_sessions(
    target: Path,
    *,
    codex_root: Path,
    output_dir: Path,
    dry_run: bool,
    print_diff: bool,
) -> tuple[list[FileResult], dict[str, object], dict[str, object]]:
    session_payload, signals_payload = reflect_sessions_payload(target, codex_root)
    summary = cast(dict[str, object], signals_payload["summary"])
    top_short_prompts = cast(
        list[dict[str, object]], signals_payload["top_short_prompts"]
    )
    patterns_md = _render_patterns(summary, top_short_prompts)

    results = [
        handle_generated_json_artifact(
            output_dir / "agent-sessions.json",
            json.dumps(session_payload, indent=2) + "\n",
            dry_run=dry_run,
            print_diff=print_diff,
        ),
        handle_generated_json_artifact(
            output_dir / "agent-signals.json",
            json.dumps(signals_payload, indent=2) + "\n",
            dry_run=dry_run,
            print_diff=print_diff,
        ),
        _handle_generated_text_artifact(
            output_dir / "agent-patterns.md",
            patterns_md,
            dry_run=dry_run,
            print_diff=print_diff,
        ),
    ]
    return results, session_payload, signals_payload
