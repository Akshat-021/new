# Tools package for PromptForge — Ollama tool-calling integration
from .web_fetch import web_fetch_tool, web_fetch_schema
from .file_reader import file_reader_tool, file_reader_schema
from .calculator import calculator_tool, calculator_schema
from .weather import weather_tool, weather_schema
from .wiki_search import wiki_search_tool, wiki_search_schema
from .code_runner import code_runner_tool, code_runner_schema
from .json_query import json_query_tool, json_query_schema
from .translator import translator_tool, translator_schema

ALL_TOOLS = [
    web_fetch_schema,
    file_reader_schema,
    calculator_schema,
    weather_schema,
    wiki_search_schema,
    code_runner_schema,
    json_query_schema,
    translator_schema,
]

TOOL_REGISTRY = {
    "web_fetch":   web_fetch_tool,
    "file_reader": file_reader_tool,
    "calculator":  calculator_tool,
    "weather":     weather_tool,
    "wiki_search": wiki_search_tool,
    "code_runner": code_runner_tool,
    "json_query":  json_query_tool,
    "translator":  translator_tool,
}

