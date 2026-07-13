import json
import re
from functools import lru_cache

from app.mcp.client import list_mcp_tools
from app.models.planner import ToolDecision
from app.services.llm import LLM


def extract_json(text: str) -> str | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None

    return match.group(0)


@lru_cache(maxsize=1)
def _tools_prompt() -> str:
    tools = list(list_mcp_tools())
    return json.dumps(tools, ensure_ascii=False, indent=2)


def decide_tool(user_message: str) -> ToolDecision:
    llm = LLM()

    prompt = f"""
You are a tool selection router.

Available MCP tools are listed below as JSON. Each tool has a name, description,
and input_schema. Choose the single best tool for the user message, and fill
arguments according to the selected tool's input_schema.

Available tools:
{_tools_prompt()}

User message:
{user_message}

You must output JSON only. Do not output markdown or explanations.

Output format when a tool is needed:
{{
  "tool": "calculator",
  "arguments": {{
    "expression": "18 ** 2"
  }}
}}

Output format when no tool is needed:
{{
  "tool": null,
  "arguments": {{}}
}}
"""

    result = llm.chat([
        {
            "role": "user",
            "content": prompt,
        }
    ])

    json_text = extract_json(result)

    if json_text is None:
        return ToolDecision(tool=None, arguments={})

    try:
        return ToolDecision.model_validate_json(json_text)
    except Exception:
        return ToolDecision(tool=None, arguments={})
