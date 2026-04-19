"""
Tool: json_query
Query a JSON structure using a dot-notation path and optionally filter arrays.
No external dependencies — pure Python.
"""

import json
from typing import Any

# ── Ollama tool schema ──────────────────────────────────────────────────────
json_query_schema = {
    "type": "function",
    "function": {
        "name": "json_query",
        "description": (
            "Extract data from a JSON string using a dot-notation path. "
            "Use this to drill into nested JSON, inspect API responses, "
            "or retrieve specific fields from complex JSON payloads. "
            "Supports array indexing (e.g. 'items.0.name') and wildcard '*' "
            "to collect a field from all items in a list."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "json_string": {
                    "type": "string",
                    "description": "A valid JSON string to query.",
                },
                "path": {
                    "type": "string",
                    "description": (
                        "Dot-notation path to the desired value. "
                        "Examples: 'user.address.city', 'results.0.score', 'items.*.name'"
                    ),
                },
            },
            "required": ["json_string", "path"],
        },
    },
}


def _traverse(obj: Any, parts: list[str]) -> Any:
    if not parts:
        return obj
    key = parts[0]
    rest = parts[1:]

    if key == "*":
        if isinstance(obj, list):
            return [_traverse(item, rest) for item in obj]
        raise KeyError("Wildcard '*' used on a non-list value")

    if isinstance(obj, dict):
        if key not in obj:
            raise KeyError(f"Key '{key}' not found in object. Available keys: {list(obj.keys())}")
        return _traverse(obj[key], rest)

    if isinstance(obj, list):
        try:
            idx = int(key)
        except ValueError:
            raise KeyError(f"Expected an integer index for list, got '{key}'")
        if idx >= len(obj) or idx < -len(obj):
            raise IndexError(f"Index {idx} out of range (list length {len(obj)})")
        return _traverse(obj[idx], rest)

    raise KeyError(f"Cannot traverse into {type(obj).__name__} with key '{key}'")


def json_query_tool(json_string: str, path: str) -> dict[str, Any]:
    """
    Parse *json_string* and return the value at *path*.

    Returns a dict with keys:
        success (bool), path (str), result (any), result_type (str), error (str|None)
    """
    try:
        data = json.loads(json_string)
    except json.JSONDecodeError as e:
        return {"success": False, "path": path, "result": None, "result_type": None, "error": f"Invalid JSON: {e}"}

    try:
        parts = [p for p in path.split(".") if p]  # split and remove empty parts
        result = _traverse(data, parts)
        return {
            "success": True,
            "path": path,
            "result": result,
            "result_type": type(result).__name__,
            "error": None,
        }
    except (KeyError, IndexError, TypeError) as e:
        return {"success": False, "path": path, "result": None, "result_type": None, "error": str(e)}
