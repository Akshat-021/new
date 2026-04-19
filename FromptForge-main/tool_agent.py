"""
tool_agent.py — Agentic loop that lets Ollama call local tools.

Strategy:
  1. First tries Ollama's NATIVE tool-calling API (works with llama3.1, qwen2.5, mistral-nemo).
  2. If the model doesn't emit structured tool_calls, falls back to PROMPT-BASED tool
     calling — the model writes JSON tool calls as text, which we parse and execute.

This makes the demo work with ANY locally available model.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import ollama

from tools import ALL_TOOLS, TOOL_REGISTRY

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "mistral"
MAX_TURNS = 8

# ── Tool descriptions for the fallback prompt ────────────────────────────────
def _build_tool_description() -> str:
    lines = []
    for tool in ALL_TOOLS:
        fn = tool["function"]
        name = fn["name"]
        desc = fn["description"].split("\n")[0]
        params = fn["parameters"].get("properties", {})
        param_str = ", ".join(
            f'{k}: {v.get("type","any")}' for k, v in params.items()
        )
        lines.append(f"  - {name}({param_str}): {desc}")
    return "\n".join(lines)

FALLBACK_SYSTEM = """You are a helpful assistant with access to tools. 
You must use these tools to answer the user's question accurately.

Available tools:
{tools}

## HOW TO CALL A TOOL
When you need to use a tool, output ONLY a JSON block like this:
```tool_call
{{"tool": "tool_name", "args": {{"param1": "value1", "param2": "value2"}}}}
```

After seeing the tool result, continue reasoning and call more tools if needed.
When you have all the information, write your final answer in plain text WITHOUT any tool_call blocks.

RULES:
- Always use tools when the question requires live data (weather, URLs, files, calculations).
- Never guess or make up numbers — use the calculator or code_runner tool instead.
- You may call multiple tools in sequence.
""".format(tools=_build_tool_description())

# ── Regex to find tool call blocks in model output ───────────────────────────
_TOOL_CALL_RE = re.compile(
    r"```tool_call\s*\n?\s*(\{.*?\})\s*\n?```",
    re.DOTALL | re.IGNORECASE,
)

# Also catch raw JSON without fences: {"tool": ..., "args": ...}
_RAW_JSON_RE = re.compile(
    r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"args"\s*:\s*(\{[^{}]*\})\s*\}',
    re.DOTALL,
)


def _parse_tool_calls_from_text(text: str) -> list[dict]:
    """Extract tool call dicts from model text output."""
    calls = []
    # Fenced blocks first
    for m in _TOOL_CALL_RE.finditer(text):
        try:
            obj = json.loads(m.group(1))
            if "tool" in obj and "args" in obj:
                calls.append(obj)
        except json.JSONDecodeError:
            pass
    # Raw JSON fallback
    if not calls:
        for m in _RAW_JSON_RE.finditer(text):
            try:
                args = json.loads(m.group(2))
                calls.append({"tool": m.group(1), "args": args})
            except json.JSONDecodeError:
                pass
    return calls


def run_tool(name: str, arguments: dict) -> str:
    """Dispatch a tool call and return its result as a JSON string."""
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return json.dumps({"success": False, "error": f"Unknown tool: '{name}'"})
    try:
        result = fn(**arguments)
        return json.dumps(result, ensure_ascii=False, default=str)
    except TypeError as e:
        return json.dumps({"success": False, "error": f"Bad arguments for '{name}': {e}"})
    except Exception as e:  # noqa: BLE001
        return json.dumps({"success": False, "error": str(e)})


# ── Native tool-calling (llama3.1, qwen2.5, mistral-nemo) ───────────────────
def _run_native(user_message: str, model: str, tools: list, system: str, max_turns: int = MAX_TURNS) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]
    turns = []
    tool_calls_made = []

    for _ in range(max_turns):
        response = ollama.chat(model=model, messages=messages, tools=tools)
        msg = response["message"]
        turns.append({"turn": len(turns) + 1, "role": "assistant", "message": msg})

        tc_list = msg.get("tool_calls") or []
        if not tc_list:
            return {
                "final_answer": (msg.get("content") or "").strip(),
                "turns": turns,
                "tool_calls_made": tool_calls_made,
                "mode": "native",
            }

        messages.append(msg)
        for tc in tc_list:
            fn_name = tc["function"]["name"]
            fn_args = tc["function"]["arguments"]
            if isinstance(fn_args, str):
                try:
                    fn_args = json.loads(fn_args)
                except json.JSONDecodeError:
                    fn_args = {}
            result_str = run_tool(fn_name, fn_args)
            tool_calls_made.append(fn_name)
            turns.append({
                "turn": len(turns) + 1, "role": "tool",
                "tool_name": fn_name, "arguments": fn_args, "result": result_str,
            })
            messages.append({"role": "tool", "content": result_str})

    # final summary
    messages.append({"role": "user", "content": "Summarize everything you found."})
    resp = ollama.chat(model=model, messages=messages)
    return {
        "final_answer": (resp["message"].get("content") or "").strip(),
        "turns": turns,
        "tool_calls_made": tool_calls_made,
        "mode": "native",
    }


# ── Prompt-based tool-calling (mistral, llama3, any model) ──────────────────
def _run_prompt_based(user_message: str, model: str, max_turns: int = MAX_TURNS) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": FALLBACK_SYSTEM},
        {"role": "user", "content": user_message},
    ]
    turns = []
    tool_calls_made = []

    for _ in range(max_turns):
        response = ollama.chat(model=model, messages=messages)
        content = (response["message"].get("content") or "").strip()
        msg_obj = {"role": "assistant", "content": content, "tool_calls": None}
        turns.append({"turn": len(turns) + 1, "role": "assistant", "message": msg_obj})

        # Check if model wants to call a tool
        tool_calls = _parse_tool_calls_from_text(content)
        if not tool_calls:
            # No tool calls → this is the final answer
            # Strip any residual fenced blocks from answer text
            clean = _TOOL_CALL_RE.sub("", content).strip()
            return {
                "final_answer": clean,
                "turns": turns,
                "tool_calls_made": tool_calls_made,
                "mode": "prompt",
            }

        # Execute each parsed tool call
        messages.append({"role": "assistant", "content": content})
        for tc in tool_calls:
            fn_name = tc.get("tool", "")
            fn_args = tc.get("args", {})
            result_str = run_tool(fn_name, fn_args)
            tool_calls_made.append(fn_name)
            turns.append({
                "turn": len(turns) + 1, "role": "tool",
                "tool_name": fn_name, "arguments": fn_args, "result": result_str,
            })
            messages.append({
                "role": "user",
                "content": f"Tool result for `{fn_name}`:\n```json\n{result_str}\n```\nNow continue.",
            })

    # Exhausted — ask for summary
    messages.append({"role": "user", "content": "Give me your final answer based on the results above."})
    resp = ollama.chat(model=model, messages=messages)
    return {
        "final_answer": (resp["message"].get("content") or "").strip(),
        "turns": turns,
        "tool_calls_made": tool_calls_made,
        "mode": "prompt",
    }


# ── Public entry point ────────────────────────────────────────────────────────
def run_tool_agent(
    user_message: str,
    system_prompt: str = "You are a helpful assistant with access to tools.",
    model: str = DEFAULT_MODEL,
    tools: list[dict] | None = None,
    verbose: bool = False,
    max_turns: int = MAX_TURNS,
) -> dict[str, Any]:
    """
    Run the agentic tool-calling loop.
    Tries native Ollama tool-calling first; falls back to prompt-based if the
    model doesn't emit structured tool_calls JSON.
    """
    if tools is None:
        tools = ALL_TOOLS

    # Step 1: Try native tool-calling
    try:
        result = _run_native(user_message, model, tools, system_prompt, max_turns=max_turns)
        if result["tool_calls_made"] or "tool_call" not in result["final_answer"]:
            return result
    except Exception as e:
        logger.info(f"Native tool-calling failed ({e}), falling back to prompt mode")

    # Step 2: Prompt-based fallback
    return _run_prompt_based(user_message, model, max_turns=max_turns)
