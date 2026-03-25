from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .actions import FileResult, _handle_generated_json_file
from .analyze import (
    _extract_text_content,
    _fetch_url,
    _normalize_url,
    _openai_chat_json,
    _stable_payload_without_timestamp,
    _utc_now_iso,
)


def _normalize_keywords(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def _build_metadata_result(url: str, text_content: str) -> dict[str, Any]:
    prompt = (
        "You are an SEO assistant specializing in LLM visibility.\n\n"
        "Analyze the following website content and return only valid JSON with keys "
        "title, description, keywords, shortDescription.\n"
        "- title: max 60 characters\n"
        "- description: max 160 characters\n"
        "- keywords: array of 5 relevant keywords\n"
        "- shortDescription: max 280 characters\n\n"
        f"URL: {url}\n"
        f"Website content:\n{text_content[:5000] or 'No content available.'}"
    )
    raw = _openai_chat_json(
        system_prompt=(
            "You are an expert SEO assistant. "
            "Return only valid JSON, no additional text or explanations."
        ),
        user_prompt=prompt,
        temperature=0.3,
    )
    description = str(raw.get("description", "") or "").strip()
    short_description = str(
        raw.get("shortDescription", "") or description or ""
    ).strip()
    return {
        "title": str(raw.get("title", "") or "").strip(),
        "description": description,
        "keywords": _normalize_keywords(raw.get("keywords", [])),
        "shortDescription": short_description,
    }


def build_metadata_payload(url: str) -> dict[str, Any]:
    normalized_url = _normalize_url(url)
    fetch = _fetch_url(normalized_url)
    text_content = _extract_text_content(fetch.text)
    payload = {
        "version": 1,
        "generated_by": "agentsgen",
        "generated_at": "",
        "url": normalized_url,
        "final_url": fetch.url,
        "mode": "ai",
        "result": _build_metadata_result(fetch.url, text_content),
    }
    payload["generated_at"] = _utc_now_iso()
    return payload


def apply_metadata(
    root: Path,
    *,
    url: str,
    output_path: Path,
    dry_run: bool = False,
) -> tuple[list[FileResult], dict[str, Any]]:
    del (
        root
    )  # Output path is explicit; keep signature aligned with other apply_* helpers.
    payload = build_metadata_payload(url)

    if output_path.exists():
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
        except Exception:
            existing = None
        if (
            isinstance(existing, dict)
            and str(existing.get("generated_by", "")) == "agentsgen"
        ):
            if _stable_payload_without_timestamp(
                existing
            ) == _stable_payload_without_timestamp(payload):
                payload["generated_at"] = str(existing.get("generated_at", "") or "")

    result = _handle_generated_json_file(
        output_path,
        json.dumps(payload, indent=2) + "\n",
        dry_run=dry_run,
        print_diff=False,
    )
    return [result], payload
