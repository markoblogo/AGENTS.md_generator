from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from .actions import FileResult, _handle_generated_json_file


_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_DESCRIPTION_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
_SCRIPT_STYLE_RE = re.compile(
    r"<(?:script|style)[^>]*>[\s\S]*?</(?:script|style)>",
    re.IGNORECASE,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_HEADING_RE = re.compile(r"<h([1-6])[^>]*>", re.IGNORECASE)
_SEMANTIC_TAGS = ("main", "article", "section", "nav", "header", "footer")
_JSON_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UrlFetch:
    url: str
    status: int
    text: str
    headers: dict[str, str]


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _normalize_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        raise ValueError("URL is required.")
    parsed = urlparse(raw)
    if not parsed.scheme:
        raw = f"https://{raw}"
        parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Provide a full http(s) URL.")
    return raw


def _fetch_url(url: str, *, timeout: float = 10.0) -> UrlFetch:
    request = Request(
        url,
        headers={
            "User-Agent": "agentsgen/0.1 (+https://github.com/markoblogo/AGENTS.md_generator)"
        },
    )
    with urlopen(request, timeout=timeout) as response:
        body = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        text = body.decode(charset, errors="replace")
        headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
        return UrlFetch(
            url=response.geturl(),
            status=getattr(response, "status", 200) or 200,
            text=text,
            headers=headers,
        )


def _probe_url(url: str, *, timeout: float = 10.0) -> bool:
    try:
        _fetch_url(url, timeout=timeout)
        return True
    except Exception:
        return False


def _extract_title(html: str) -> str:
    match = _TITLE_RE.search(html)
    if not match:
        return ""
    return _WHITESPACE_RE.sub(" ", match.group(1)).strip()


def _extract_meta_description(html: str) -> str:
    match = _META_DESCRIPTION_RE.search(html)
    if not match:
        return ""
    return _WHITESPACE_RE.sub(" ", match.group(1)).strip()


def _extract_text_content(html: str) -> str:
    text = _SCRIPT_STYLE_RE.sub(" ", html)
    text = _TAG_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _semantic_tag_count(html: str) -> int:
    count = 0
    for tag in _SEMANTIC_TAGS:
        count += len(re.findall(rf"<{tag}\b", html, flags=re.IGNORECASE))
    return count


def _heading_count(html: str) -> int:
    return len(_HEADING_RE.findall(html))


def _has_json_ld(html: str) -> bool:
    return bool(_JSON_LD_RE.search(html))


def _heuristic_factors(
    html: str, text_content: str, *, has_llms_txt: bool, has_sitemap: bool
) -> tuple[dict[str, int], dict[str, Any]]:
    title = _extract_title(html)
    description = _extract_meta_description(html)
    headings = _heading_count(html)
    semantic_tags = _semantic_tag_count(html)
    json_ld = _has_json_ld(html)
    word_count = len([part for part in text_content.split(" ") if part])

    factors: dict[str, int] = {}
    evidence: dict[str, Any] = {
        "title_present": bool(title),
        "meta_description_present": bool(description),
        "headings_count": headings,
        "semantic_tags_count": semantic_tags,
        "json_ld_present": json_ld,
        "word_count": word_count,
        "llms_txt_present": has_llms_txt,
        "sitemap_present": has_sitemap,
    }

    factors["llms_txt"] = 30 if has_llms_txt else 0
    factors["sitemap"] = 10 if has_sitemap else 0

    if title and description:
        factors["meta_tags"] = 15
    elif title or description:
        factors["meta_tags"] = 8
    else:
        factors["meta_tags"] = 0

    if headings >= 3:
        factors["heading_structure"] = 15
    elif headings >= 1:
        factors["heading_structure"] = 8
    else:
        factors["heading_structure"] = 0

    if semantic_tags >= 3:
        factors["semantic_html"] = 10
    elif semantic_tags >= 1:
        factors["semantic_html"] = 5
    else:
        factors["semantic_html"] = 0

    factors["structured_data"] = 10 if json_ld else 0

    if word_count >= 300:
        factors["content_clarity"] = 10
    elif word_count >= 100:
        factors["content_clarity"] = 5
    else:
        factors["content_clarity"] = 0

    return factors, evidence


def _visibility(score: int) -> str:
    if score > 70:
        return "high"
    if score > 40:
        return "medium"
    return "low"


def _recommendations(factors: dict[str, int], evidence: dict[str, Any]) -> list[str]:
    recommendations: list[str] = []
    if not evidence.get("llms_txt_present"):
        recommendations.append(
            "Create and publish an llms.txt file to improve AI discoverability."
        )
    if not evidence.get("sitemap_present"):
        recommendations.append(
            "Publish a sitemap.xml file for crawlable site structure."
        )
    if factors.get("meta_tags", 0) < 15:
        recommendations.append("Add both a clear HTML title and meta description.")
    if factors.get("heading_structure", 0) < 15:
        recommendations.append(
            "Strengthen heading structure with a clear H1 and section headings."
        )
    if factors.get("semantic_html", 0) < 10:
        recommendations.append(
            "Use semantic HTML landmarks such as main, article, section, and nav."
        )
    if factors.get("structured_data", 0) == 0:
        recommendations.append(
            "Add schema.org JSON-LD where it reflects real page entities."
        )
    if factors.get("content_clarity", 0) < 10:
        recommendations.append(
            "Expose more crawlable text content instead of relying on sparse hero-only copy."
        )
    if not recommendations:
        recommendations.append(
            "This site already shows strong AI-oriented discoverability signals."
        )
    return recommendations


def _summary(score: int, visibility: str) -> str:
    if visibility == "high":
        return f"Strong baseline AI discoverability signals detected ({score}/100)."
    if visibility == "medium":
        return f"Mixed AI discoverability signals detected ({score}/100)."
    return f"Weak AI discoverability signals detected ({score}/100)."


def _openai_review(url: str, html: str, text_content: str) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required when using --use-ai.")

    prompt = (
        "Analyze this website for AI discoverability. "
        "Return only valid JSON with keys summary, reasons, recommendations. "
        "Keep reasons and recommendations short.\n\n"
        f"URL: {url}\n"
        f"Content sample:\n{text_content[:2000]}"
    )
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert reviewer. Return only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }
    request = Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        raw = json.loads(response.read().decode("utf-8"))
    content = raw["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            raise ValueError("OpenAI response did not contain valid JSON.")
        return json.loads(match.group(0))


def _stable_payload_without_timestamp(payload: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(payload))
    clone["generated_at"] = ""
    return json.dumps(clone, sort_keys=True, separators=(",", ":"))


def build_analysis_payload(url: str, *, use_ai: bool = False) -> dict[str, Any]:
    normalized_url = _normalize_url(url)
    fetch = _fetch_url(normalized_url)
    html = fetch.text
    text_content = _extract_text_content(html)
    has_llms_txt = _probe_url(urljoin(fetch.url.rstrip("/") + "/", "llms.txt"))
    has_sitemap = _probe_url(urljoin(fetch.url.rstrip("/") + "/", "sitemap.xml"))
    factors, evidence = _heuristic_factors(
        html, text_content, has_llms_txt=has_llms_txt, has_sitemap=has_sitemap
    )
    score = sum(factors.values())
    visibility = _visibility(score)
    payload: dict[str, Any] = {
        "version": 1,
        "generated_by": "agentsgen",
        "generated_at": "",
        "url": normalized_url,
        "final_url": fetch.url,
        "mode": "ai-assisted" if use_ai else "heuristic",
        "score": score,
        "visibility": visibility,
        "summary": _summary(score, visibility),
        "factors": factors,
        "evidence": evidence,
        "recommendations": _recommendations(factors, evidence),
    }
    if use_ai:
        payload["ai_review"] = _openai_review(fetch.url, html, text_content)
    payload["generated_at"] = _utc_now_iso()
    return payload


def apply_analysis(
    root: Path,
    *,
    url: str,
    output_path: Path,
    use_ai: bool = False,
    dry_run: bool = False,
) -> tuple[list[FileResult], dict[str, Any]]:
    del (
        root
    )  # Output path is explicit; keep signature aligned with other apply_* helpers.
    payload = build_analysis_payload(url, use_ai=use_ai)

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
