"""
Tool: file_reader
Reads a local file and returns its content.
Supports plain text, .csv, .json, .md, .py, .yaml, .toml, etc.
"""

import json
import os
from typing import Any

# ── Ollama tool schema ──────────────────────────────────────────────────────
file_reader_schema = {
    "type": "function",
    "function": {
        "name": "file_reader",
        "description": (
            "Read the content of a local file on disk. "
            "Use this when the user asks you to inspect, summarize, or analyze "
            "a file that exists on their machine."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file to read.",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Max characters to return. Default 4000.",
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding. Default 'utf-8'.",
                },
            },
            "required": ["path"],
        },
    },
}


# ── Implementation ──────────────────────────────────────────────────────────
_ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".json", ".csv",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".log", ".html",
    ".css", ".sh", ".rs", ".go", ".java", ".c", ".cpp", ".h",
}

_MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB safety limit


def file_reader_tool(path: str, max_chars: int = 4000, encoding: str = "utf-8") -> dict[str, Any]:
    """
    Read a local file and return its text content.

    Returns a dict with keys:
        success (bool), path (str), content (str),
        size_bytes (int), extension (str), error (str | None)
    """
    abs_path = os.path.abspath(path)
    ext = os.path.splitext(abs_path)[1].lower()

    if not os.path.exists(abs_path):
        return {"success": False, "path": abs_path, "content": "", "error": "File not found"}

    if not os.path.isfile(abs_path):
        return {"success": False, "path": abs_path, "content": "", "error": "Path is not a file"}

    size = os.path.getsize(abs_path)
    if size > _MAX_SIZE_BYTES:
        return {
            "success": False, "path": abs_path, "content": "",
            "error": f"File too large ({size} bytes). Limit is {_MAX_SIZE_BYTES} bytes."
        }

    if ext not in _ALLOWED_EXTENSIONS:
        return {
            "success": False, "path": abs_path, "content": "",
            "error": f"Extension '{ext}' is not in the allowed list: {sorted(_ALLOWED_EXTENSIONS)}"
        }

    try:
        with open(abs_path, encoding=encoding, errors="replace") as fh:
            content = fh.read(max_chars)

        # Pretty-print JSON for readability
        if ext == ".json":
            try:
                parsed = json.loads(content)
                content = json.dumps(parsed, indent=2, ensure_ascii=False)[:max_chars]
            except json.JSONDecodeError:
                pass  # return raw if not valid JSON

        return {
            "success": True,
            "path": abs_path,
            "content": content,
            "size_bytes": size,
            "extension": ext,
            "error": None,
        }

    except Exception as e:  # noqa: BLE001
        return {"success": False, "path": abs_path, "content": "", "error": str(e)}
