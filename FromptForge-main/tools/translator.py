"""
Tool: translator
Translates text between languages using the MyMemory free translation API.
No API key required for moderate usage.
"""

import json
import ssl
import urllib.request
import urllib.parse
from typing import Any

import certifi

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

# ── Ollama tool schema ──────────────────────────────────────────────────────
translator_schema = {
    "type": "function",
    "function": {
        "name": "translator",
        "description": (
            "Translate text from one language to another. "
            "Use this whenever the user asks you to translate something or "
            "when you need to convert content to a different language. "
            "Supports 50+ languages."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to translate.",
                },
                "target_language": {
                    "type": "string",
                    "description": (
                        "Target language name or code, e.g. 'Hindi', 'French', "
                        "'Spanish', 'Japanese', 'Arabic', 'de', 'fr', 'ja'."
                    ),
                },
                "source_language": {
                    "type": "string",
                    "description": "Source language name or code. Default 'auto' (auto-detect).",
                },
            },
            "required": ["text", "target_language"],
        },
    },
}

# Language name → ISO 639-1 code mapping
_LANG_MAP = {
    "english": "en", "hindi": "hi", "spanish": "es", "french": "fr",
    "german": "de", "italian": "it", "portuguese": "pt", "russian": "ru",
    "japanese": "ja", "chinese": "zh", "arabic": "ar", "korean": "ko",
    "dutch": "nl", "polish": "pl", "turkish": "tr", "swedish": "sv",
    "norwegian": "no", "danish": "da", "finnish": "fi", "greek": "el",
    "czech": "cs", "hungarian": "hu", "romanian": "ro", "thai": "th",
    "vietnamese": "vi", "indonesian": "id", "malay": "ms", "ukrainian": "uk",
    "bengali": "bn", "tamil": "ta", "telugu": "te", "gujarati": "gu",
    "marathi": "mr", "punjabi": "pa", "urdu": "ur", "persian": "fa",
    "hebrew": "he", "swahili": "sw", "afrikaans": "af", "catalan": "ca",
    "croatian": "hr", "slovak": "sk", "slovenian": "sl", "latvian": "lv",
    "lithuanian": "lt", "estonian": "et", "serbian": "sr", "bulgarian": "bg",
    "auto": "auto",
}


def _resolve_code(lang: str) -> str:
    """Convert language name to ISO code, or return as-is if already a code."""
    lang = lang.strip().lower()
    if lang in _LANG_MAP:
        return _LANG_MAP[lang]
    # Maybe it's already a code like 'hi', 'fr'
    if len(lang) in (2, 3):
        return lang
    # Partial match
    for name, code in _LANG_MAP.items():
        if lang in name or name in lang:
            return code
    return lang


def translator_tool(
    text: str,
    target_language: str,
    source_language: str = "auto",
) -> dict[str, Any]:
    """
    Translate *text* to *target_language* using the MyMemory free API.

    Returns a dict with keys:
        success, original_text, translated_text,
        source_language, target_language, error
    """
    if not text.strip():
        return {"success": False, "error": "Empty text provided"}

    src_code = _resolve_code(source_language)
    tgt_code = _resolve_code(target_language)
    lang_pair = f"{src_code}|{tgt_code}" if src_code != "auto" else f"en|{tgt_code}"

    try:
        url = (
            "https://api.mymemory.translated.net/get?"
            + urllib.parse.urlencode({
                "q": text[:500],  # API limit
                "langpair": lang_pair,
            })
        )
        req = urllib.request.Request(url, headers={"User-Agent": "PromptForge/1.0"})
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
            data = json.loads(resp.read().decode())

        status = data.get("responseStatus", 0)
        if status != 200:
            return {
                "success": False, "error": f"API error {status}: {data.get('responseDetails', '')}"
            }

        translated = data["responseData"]["translatedText"]
        detected_src = data.get("responseData", {}).get("detectedLanguage", src_code) or src_code

        return {
            "success": True,
            "original_text": text,
            "translated_text": translated,
            "source_language": detected_src,
            "target_language": tgt_code,
            "error": None,
        }

    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": str(e)}
