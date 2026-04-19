"""
Tool: calculator
Evaluates a safe mathematical expression and returns the result.
Uses Python's ast module for safe evaluation — no exec/eval on arbitrary code.
"""

import ast
import math
import operator
from typing import Any

# ── Ollama tool schema ──────────────────────────────────────────────────────
calculator_schema = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": (
            "Evaluate a mathematical expression and return the numeric result. "
            "Supports basic arithmetic (+, -, *, /), exponentiation (**), "
            "modulus (%), parentheses, and common math functions like "
            "sqrt(), log(), sin(), cos(), abs(), round(), pi, e."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A valid mathematical expression, e.g. '2 ** 10 + sqrt(144)'.",
                },
            },
            "required": ["expression"],
        },
    },
}


# ── Safe AST evaluator ──────────────────────────────────────────────────────
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
    "gcd": math.gcd,
    "hypot": math.hypot,
    "pow": math.pow,
}

_SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value!r}")
    elif isinstance(node, ast.Name):
        if node.id in _SAFE_CONSTANTS:
            return _SAFE_CONSTANTS[node.id]
        raise ValueError(f"Unknown name: '{node.id}'")
    elif isinstance(node, ast.BinOp):
        op_fn = _SAFE_OPERATORS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op_fn(_safe_eval(node.left), _safe_eval(node.right))
    elif isinstance(node, ast.UnaryOp):
        op_fn = _SAFE_OPERATORS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op_fn(_safe_eval(node.operand))
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls are allowed")
        fn = _SAFE_FUNCTIONS.get(node.func.id)
        if fn is None:
            raise ValueError(f"Function '{node.func.id}' is not allowed")
        args = [_safe_eval(a) for a in node.args]
        return fn(*args)
    else:
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")


# ── Public tool function ────────────────────────────────────────────────────
def calculator_tool(expression: str) -> dict[str, Any]:
    """
    Safely evaluate a math expression.

    Returns a dict with keys:
        success (bool), expression (str), result (float | int | None), error (str | None)
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval(tree)
        # Coerce complex to string
        if isinstance(result, complex):
            result_str = str(result)
            return {"success": True, "expression": expression, "result": result_str, "error": None}
        # Round floats to avoid floating point noise
        if isinstance(result, float) and result == int(result) and not math.isinf(result):
            result = int(result)
        return {"success": True, "expression": expression, "result": result, "error": None}
    except Exception as e:  # noqa: BLE001
        return {"success": False, "expression": expression, "result": None, "error": str(e)}
