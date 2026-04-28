"""
Language detection and ES→EN translation.
"""
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

MAX_TRANSLATE_CHARS = 4500  # Google Translate free limit per call


def detect_language(text: str) -> str:
    if not text or len(text) < 20:
        return "en"
    try:
        return detect(text)
    except LangDetectException:
        return "en"


def translate_to_english(text: str) -> str:
    if not text:
        return ""
    chunk = text[:MAX_TRANSLATE_CHARS]
    try:
        return GoogleTranslator(source="auto", target="en").translate(chunk)
    except Exception as e:
        print(f"[Language] Translation failed: {e}")
        return text


def process_language(item: dict) -> dict:
    raw = item.get("raw_text") or item.get("excerpt") or item.get("title") or ""

    lang = item.get("original_language") or detect_language(raw)
    item["original_language"] = lang

    if lang == "es":
        item["translated_text"] = translate_to_english(raw)
    else:
        item["translated_text"] = raw

    return item
