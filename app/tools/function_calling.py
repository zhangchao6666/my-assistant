# app/tools/function_calling.py

import json
from typing import Any


def mcp_tools_to_openai_tools(
    mcp_tools: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description") or "",
                "parameters": tool["input_schema"],
            },
        }
        for tool in mcp_tools
    ]

def parse_tool_call_arguments(arguments: str | None) -> dict[str, Any]:
    if not arguments:
        return {}

    try:
        parsed = json.loads(arguments)
    except json.JSONDecodeError:
        return {}

    if not isinstance(parsed, dict):
        return {}

    return parsed


def parse_tool_call_arguments_with_error(arguments: str | None) -> tuple[dict[str, Any], str | None]:
    if not arguments:
        return {}, None

    try:
        parsed = json.loads(arguments)
    except json.JSONDecodeError as exc:
        return {}, f"Invalid JSON arguments: {exc}"

    if not isinstance(parsed, dict):
        return {}, "Tool arguments must be a JSON object."

    return parsed, None
