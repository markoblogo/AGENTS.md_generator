from __future__ import annotations

from collections import defaultdict
import re
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_DESCRIPTION_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
_WHITESPACE_RE = re.compile(r"\s+")


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


def _fetch_url(url: str, *, timeout: float = 10.0) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "agentsgen/0.1 (+https://github.com/markoblogo/AGENTS.md_generator)"
        },
    )
    with urlopen(request, timeout=timeout) as response:
        body = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return body.decode(charset, errors="replace")


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


def _site_base_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _fetch_optional_text(url: str) -> str:
    try:
        return _fetch_url(url)
    except Exception:
        return ""


def _parse_sitemap_urls(xml_text: str) -> list[str]:
    if not xml_text.strip():
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    urls: list[str] = []
    for loc in root.findall(".//{*}loc"):
        value = (loc.text or "").strip()
        if value:
            urls.append(value)
    return sorted(dict.fromkeys(urls))


def _path_label(url: str, base_url: str) -> str:
    parsed = urlparse(url)
    base_parsed = urlparse(base_url)
    if parsed.netloc and parsed.netloc != base_parsed.netloc:
        return url
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return path


def _group_paths(urls: Iterable[str], base_url: str) -> list[tuple[str, int]]:
    counts: dict[str, int] = defaultdict(int)
    for url in urls:
        label = _path_label(url, base_url)
        if label == "/":
            group = "/"
        else:
            parts = [part for part in label.split("/") if part]
            group = f"/{parts[0]}" if parts else "/"
        counts[group] += 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def build_site_llms_manifest(site_url: str) -> str:
    normalized_url = _normalize_url(site_url)
    homepage_html = _fetch_url(normalized_url)
    base_url = _site_base_url(normalized_url)
    sitemap_url = urljoin(base_url.rstrip("/") + "/", "sitemap.xml")
    sitemap_text = _fetch_optional_text(sitemap_url)
    sitemap_urls = _parse_sitemap_urls(sitemap_text)

    title = _extract_title(homepage_html) or base_url
    description = _extract_meta_description(homepage_html) or (
        "Website manifest generated from the homepage and sitemap."
    )
    representative_urls = sitemap_urls[:12] if sitemap_urls else [normalized_url]
    grouped = _group_paths(
        representative_urls if sitemap_urls else [normalized_url], base_url
    )

    lines = [
        f"# {title}",
        "",
        f"Source: {base_url}",
        "Type: Website llms.txt manifest",
        f"Total URLs: {len(sitemap_urls) if sitemap_urls else 1}",
        "",
        "## About",
        description,
        "",
        "## Key sections",
    ]

    for group, count in grouped[:8]:
        lines.append(f"- {group}: {count} page{'s' if count != 1 else ''}")

    lines.extend(["", "## Representative pages"])
    for url in representative_urls:
        lines.append(f"- {_path_label(url, base_url)}")

    lines.extend(["", "## Notes"])
    if sitemap_urls:
        lines.append("- Derived from the public sitemap plus the homepage.")
    else:
        lines.append("- Derived from the homepage only; no sitemap.xml was found.")
    lines.append("- Generated deterministically by agentsgen.")

    return "\n".join(lines).rstrip() + "\n"
