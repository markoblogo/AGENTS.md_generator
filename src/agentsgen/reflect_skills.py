from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import cast

from .generated_artifacts import handle_generated_json_artifact
from .reflect_sessions import (
    _handle_generated_text_artifact,
    load_codex_session_transcripts,
    utc_now_iso,
)
from .result_types import FileResult
from .validators import (
    validate_reflect_skill_usage_payload,
)


SKILL_TOKEN_RE = re.compile(r"\$([A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)?)")
SKILL_PHRASE_RE = re.compile(
    r"\b(?:use|using|with|apply|run|try)\s+([A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)?)\s+skill\b",
    re.IGNORECASE,
)
SKILL_CARD_RE = re.compile(
    r"\b([A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)?)\b(?=[`\"']?\s+(?:skill|skills)\b)",
    re.IGNORECASE,
)
SKILL_STOPWORDS = {"use", "using", "with", "apply", "run", "try", "skill", "skills"}


def _normalize_skill_name(raw: str) -> str:
    return raw.strip().strip("`'\"").lower()


def _extract_skill_mentions(text: str) -> list[str]:
    mentions: list[str] = []
    for match in SKILL_TOKEN_RE.finditer(text):
        mentions.append(_normalize_skill_name(match.group(1)))
    for match in SKILL_PHRASE_RE.finditer(text):
        mentions.append(_normalize_skill_name(match.group(1)))
    for match in SKILL_CARD_RE.finditer(text):
        candidate = _normalize_skill_name(match.group(1))
        if (
            len(candidate) >= 3
            and candidate not in SKILL_STOPWORDS
            and candidate not in mentions
        ):
            mentions.append(candidate)
    return sorted(set(mentions))


def _bucket_for(
    *,
    activations: int,
    redirect_rate: float,
    plan_first_ratio: float,
) -> str:
    if activations <= 1:
        return "low-signal"
    if redirect_rate >= 1.5:
        return "review"
    if plan_first_ratio >= 0.5 and redirect_rate <= 1.0:
        return "keep"
    return "watch"


def _render_effectiveness(
    *,
    repo_path: str,
    summary: dict[str, object],
    skills: list[dict[str, object]],
) -> str:
    session_count = cast(int, summary["session_count"])
    skill_activation_count = cast(int, summary["skill_activation_count"])
    unique_skills = cast(int, summary["unique_skills"])
    lines = [
        "---",
        'generated_by: "agentsgen"',
        'artifact: "skill-effectiveness"',
        "experimental: true",
        "---",
        "",
        "# Skill Effectiveness Audit",
        "",
        f"- Repo: `{repo_path}`",
        f"- Sessions scanned: `{session_count}`",
        f"- Skill activations detected: `{skill_activation_count}`",
        f"- Unique skills mentioned: `{unique_skills}`",
        "",
        "## Buckets",
        "",
    ]
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in skills:
        grouped[str(item["bucket"])].append(item)
    for bucket in ("keep", "watch", "review", "low-signal"):
        rows = grouped.get(bucket, [])
        if not rows:
            continue
        lines.append(f"### {bucket}")
        lines.append("")
        for item in rows:
            lines.append(
                f"- `{item['skill']}`: activations={item['activations']}, "
                f"sessions={item['sessions']}, redirects/session={item['redirects_per_session']}, "
                f"plan-first={item['plan_first_ratio']}%"
            )
        lines.append("")
    lines.extend(
        [
            "## Notes",
            "",
            "- This audit uses transcript-derived skill mentions, not verified runtime activation hooks.",
            "- Treat `keep/watch/review/low-signal` as editing guidance for skill docs, not as a hard quality score.",
            "",
        ]
    )
    return "\n".join(lines)


def reflect_skills_payload(
    target: Path, codex_root: Path
) -> tuple[dict[str, object], str]:
    transcripts = load_codex_session_transcripts(target, codex_root)
    skill_rows: dict[str, dict[str, object]] = {}
    total_activations = 0
    sessions_with_skills = 0

    for transcript in transcripts:
        mentioned: set[str] = set()
        for message in transcript.user_messages:
            mentioned.update(_extract_skill_mentions(message))
        if not mentioned:
            continue
        sessions_with_skills += 1
        total_activations += len(mentioned)
        for skill in sorted(mentioned):
            row = skill_rows.setdefault(
                skill,
                {
                    "skill": skill,
                    "sessions": 0,
                    "activations": 0,
                    "plan_first_sessions": 0,
                    "redirect_total": 0,
                    "long_sessions": 0,
                    "session_ids": [],
                },
            )
            row["sessions"] = cast(int, row["sessions"]) + 1
            row["activations"] = cast(int, row["activations"]) + 1
            row["plan_first_sessions"] = cast(int, row["plan_first_sessions"]) + int(
                transcript.summary.plan_first
            )
            row["redirect_total"] = (
                cast(int, row["redirect_total"]) + transcript.summary.redirects
            )
            row["long_sessions"] = cast(int, row["long_sessions"]) + int(
                transcript.summary.long_session
            )
            cast(list[str], row["session_ids"]).append(transcript.summary.session_id)

    skills: list[dict[str, object]] = []
    for skill, row in sorted(skill_rows.items()):
        sessions = cast(int, row["sessions"])
        activations = cast(int, row["activations"])
        plan_first_sessions = cast(int, row["plan_first_sessions"])
        redirect_total = cast(int, row["redirect_total"])
        long_sessions = cast(int, row["long_sessions"])
        redirects_per_session = round(redirect_total / sessions, 2) if sessions else 0.0
        plan_first_ratio = (
            int((plan_first_sessions * 100) / sessions) if sessions else 0
        )
        long_session_ratio = int((long_sessions * 100) / sessions) if sessions else 0
        bucket = _bucket_for(
            activations=activations,
            redirect_rate=redirects_per_session,
            plan_first_ratio=plan_first_ratio / 100.0,
        )
        skills.append(
            {
                "skill": skill,
                "sessions": sessions,
                "activations": activations,
                "plan_first_ratio": plan_first_ratio,
                "redirect_total": redirect_total,
                "redirects_per_session": redirects_per_session,
                "long_session_ratio": long_session_ratio,
                "bucket": bucket,
                "session_ids": cast(list[str], row["session_ids"]),
            }
        )

    usage_payload: dict[str, object] = {
        "version": 1,
        "generated_by": "agentsgen",
        "generated_at": utc_now_iso(),
        "repo": {"path": str(target.resolve())},
        "source": {"tool": "codex", "root": str(codex_root)},
        "summary": {
            "session_count": len(transcripts),
            "sessions_with_skills": sessions_with_skills,
            "skill_activation_count": total_activations,
            "unique_skills": len(skills),
        },
        "skills": skills,
    }
    validate_reflect_skill_usage_payload(usage_payload)
    effectiveness_md = _render_effectiveness(
        repo_path=str(target.resolve()),
        summary=cast(dict[str, object], usage_payload["summary"]),
        skills=skills,
    )
    return usage_payload, effectiveness_md


def apply_reflect_skills(
    target: Path,
    *,
    codex_root: Path,
    output_dir: Path,
    dry_run: bool,
    print_diff: bool,
) -> tuple[list[FileResult], dict[str, object]]:
    usage_payload, effectiveness_md = reflect_skills_payload(target, codex_root)
    results = [
        handle_generated_json_artifact(
            output_dir / "skill-usage.json",
            json.dumps(usage_payload, indent=2) + "\n",
            dry_run=dry_run,
            print_diff=print_diff,
        ),
        _handle_generated_text_artifact(
            output_dir / "skill-effectiveness.md",
            effectiveness_md,
            dry_run=dry_run,
            print_diff=print_diff,
        ),
    ]
    return results, usage_payload
