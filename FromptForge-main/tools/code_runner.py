"""
Tool: code_runner
Executes a Python code snippet in a sandboxed subprocess and returns stdout/stderr.
Imposes strict time and output limits for safety.
"""

import subprocess
import sys
import textwrap
from typing import Any

# ── Ollama tool schema ──────────────────────────────────────────────────────
code_runner_schema = {
    "type": "function",
    "function": {
        "name": "code_runner",
        "description": (
            "Run a Python 3 code snippet and return its stdout output and any errors. "
            "Use this to verify logic, perform computations, generate data, test algorithms, "
            "or demonstrate code results. Only pure Python (stdlib) is available."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Valid Python 3 code to execute. Can be multi-line.",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Max execution time in seconds (1–15). Default 10.",
                },
            },
            "required": ["code"],
        },
    },
}

_MAX_OUTPUT_CHARS = 4000

# Simple denylist — block obviously dangerous calls
_BANNED_TOKENS = [
    "import os", "import sys", "import subprocess", "import socket",
    "import shutil", "import ctypes", "__import__", "open(",
    "exec(", "eval(", "compile(", "globals(", "locals(",
    "getattr(", "setattr(", "delattr(",
]


def code_runner_tool(code: str, timeout_seconds: int = 10) -> dict[str, Any]:
    """
    Execute *code* in a subprocess with strict limits.

    Returns a dict with keys:
        success (bool), stdout (str), stderr (str), exit_code (int), timed_out (bool), error (str|None)
    """
    timeout_seconds = max(1, min(timeout_seconds, 15))

    # Basic safety check
    code_lower = code.lower()
    for token in _BANNED_TOKENS:
        if token in code_lower:
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
                "timed_out": False,
                "error": f"Blocked: code contains disallowed token '{token}'",
            }

    # Wrap code to capture print output
    safe_code = textwrap.dedent(code)

    try:
        result = subprocess.run(
            [sys.executable, "-c", safe_code],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        stdout = result.stdout[:_MAX_OUTPUT_CHARS]
        stderr = result.stderr[:_MAX_OUTPUT_CHARS]
        return {
            "success": result.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
            "timed_out": False,
            "error": None,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "timed_out": True,
            "error": f"Code timed out after {timeout_seconds}s",
        }
    except Exception as e:  # noqa: BLE001
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "timed_out": False,
            "error": str(e),
        }
