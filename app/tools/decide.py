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
You are a tool selection router for a multi-step agent.

Available MCP tools are listed below as JSON. Each tool has a name, description,
and input_schema. Choose at most one best next tool call for the current step,
and fill arguments according to the selected tool's input_schema.

Available tools:
{_tools_prompt()}

Routing rules:
1. For current weather, current temperature, rain, heat/cold, or comparing weather/temperature between cities, use the weather tool. Do not use rag for current weather or time-sensitive facts.
2. If the user asks to compare weather or temperature across multiple cities, call weather for one missing city per step. If observations already include one city but not another, call weather for the missing city next.
3. Use calculator only for arithmetic expressions or numeric calculations.
4. Use rag only for questions about the local knowledge base or stored documents, not for real-time weather, current events, or arithmetic.
5. If the observations are enough to answer the original user question, return no tool.

Current decision context:
{user_message}

You must output JSON only. Do not output markdown or explanations.

Output format when a tool is needed:
{{
  "tool": "weather",
  "arguments": {{
    "city": "成都"
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
