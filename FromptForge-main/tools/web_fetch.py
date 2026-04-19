"""
Tool: web_fetch
Fetches a URL and returns the plain-text content (stripped of HTML tags).
The model can use this to retrieve live web pages, APIs, or any public URL.
"""

import re
import ssl
import urllib.request
import urllib.error
from typing import Any

import certifi

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

# ── Ollama tool schema ──────────────────────────────────────────────────────
web_fetch_schema = {
    "type": "function",
    "function": {
        "name": "web_fetch",
        "description": (
            "Fetch the raw text content of any public URL (web page, REST endpoint, "
            "plain-text file, etc.). Use it whenever you need live information from "
            "the internet that is not in your training data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The fully-qualified URL to fetch (must start with http:// or https://).",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters to return. Default 3000.",
                },
            },
            "required": ["url"],
        },
    },
}


# ── Implementation ──────────────────────────────────────────────────────────
def web_fetch_tool(url: str, max_chars: int = 3000) -> dict[str, Any]:
    """
    Download *url* and return cleaned plain-text.

    Returns a dict with keys:
        success (bool), content (str), url (str), error (str | None)
    """
    if not url.startswith(("http://", "https://")):
        return {"success": False, "url": url, "content": "", "error": "URL must start with http:// or https://"}

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "PromptForge/1.0 (tool-demo; educational)"},
        )
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        # Strip HTML tags
        text = re.sub(r"<[^>]+>", " ", raw)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        text = text[:max_chars]

        return {"success": True, "url": url, "content": text, "error": None}

    except urllib.error.HTTPError as e:
        return {"success": False, "url": url, "content": "", "error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"success": False, "url": url, "content": "", "error": str(e.reason)}
    except Exception as e:  # noqa: BLE001
        return {"success": False, "url": url, "content": "", "error": str(e)}
