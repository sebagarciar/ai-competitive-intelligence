"""
Text cleaning and field standardization.
"""
import re
import html
from datetime import datetime, timezone


_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

MAX_RAW_TEXT = 2000


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = _HTML_TAG.sub(" ", text)
    text = _CONTROL.sub("", text)
    text = _WHITESPACE.sub(" ", text)
    return text.strip()


def truncate(text: str, max_chars: int = MAX_RAW_TEXT) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last_space = cut.rfind(" ")
    return cut[:last_space] if last_space > max_chars // 2 else cut


def normalize_date(raw: str | None) -> str | None:
    if not raw:
        return None
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(raw.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue
    return raw


def normalize_item(item: dict) -> dict:
    item["title"] = clean_text(item.get("title"))
    item["excerpt"] = clean_text(item.get("excerpt"))
    raw = clean_text(item.get("raw_text") or item.get("excerpt") or item.get("title"))
    item["raw_text"] = truncate(raw)
    item["published_at"] = normalize_date(item.get("published_at"))
    return item
