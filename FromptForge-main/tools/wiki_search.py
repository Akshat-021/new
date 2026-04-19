"""
Tool: wiki_search
Searches Wikipedia and returns a brief article summary.
Uses the Wikipedia REST API (no key needed).
"""

import json
import ssl
import urllib.request
import urllib.parse
from typing import Any

import certifi

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

# ── Ollama tool schema ──────────────────────────────────────────────────────
wiki_search_schema = {
    "type": "function",
    "function": {
        "name": "wiki_search",
        "description": (
            "Search Wikipedia for a topic and return a plain-text summary of the "
            "best matching article. Use this to look up facts, definitions, people, "
            "events, concepts, or anything that may be on Wikipedia."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search term or topic to look up on Wikipedia.",
                },
                "sentences": {
                    "type": "integer",
                    "description": "Number of summary sentences to return (1-10). Default 5.",
                },
                "language": {
                    "type": "string",
                    "description": "Wikipedia language code, e.g. 'en', 'hi', 'de'. Default 'en'.",
                },
            },
            "required": ["query"],
        },
    },
}


def wiki_search_tool(query: str, sentences: int = 5, language: str = "en") -> dict[str, Any]:
    """
    Search Wikipedia and return a summary.

    Returns a dict with keys:
        success, query, title, summary, url, error
    """
    sentences = max(1, min(sentences, 10))

    try:
        # Step 1 — Search for the best article title
        search_url = (
            f"https://{language}.wikipedia.org/w/api.php?"
            + urllib.parse.urlencode({
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": 1,
                "format": "json",
                "utf8": 1,
            })
        )
        req = urllib.request.Request(search_url, headers={"User-Agent": "PromptForge/1.0"})
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
            search_data = json.loads(resp.read().decode())

        search_results = search_data.get("query", {}).get("search", [])
        if not search_results:
            return {"success": False, "query": query, "error": "No Wikipedia articles found"}

        title = search_results[0]["title"]

        # Step 2 — Fetch the article extract (summary)
        extract_url = (
            f"https://{language}.wikipedia.org/w/api.php?"
            + urllib.parse.urlencode({
                "action": "query",
                "titles": title,
                "prop": "extracts",
                "exsentences": sentences,
                "explaintext": True,
                "exsectionformat": "plain",
                "format": "json",
                "utf8": 1,
            })
        )
        req2 = urllib.request.Request(extract_url, headers={"User-Agent": "PromptForge/1.0"})
        with urllib.request.urlopen(req2, timeout=10, context=_SSL_CTX) as resp2:
            extract_data = json.loads(resp2.read().decode())

        pages = extract_data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()))
        summary = page.get("extract", "").strip()
        article_url = f"https://{language}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"

        return {
            "success": True,
            "query": query,
            "title": title,
            "summary": summary,
            "url": article_url,
            "error": None,
        }

    except Exception as e:  # noqa: BLE001
        return {"success": False, "query": query, "error": str(e)}
