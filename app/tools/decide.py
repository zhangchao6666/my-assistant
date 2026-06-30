import json
import re

from app.models.planner import ToolDecision
from app.services.llm import LLM


def extract_json(text: str) -> str | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None

    return match.group(0)


def decide_tool(user_message: str) -> ToolDecision:
    llm = LLM()

    prompt = f"""
你是工具选择器。

可用工具：
1. weather：查询城市天气。参数：city
判断规则：
只要用户在询问某个城市的天气、温度、气温、冷热、下雨、下雪、带伞，都应该调用 weather。

示例：
用户：成都今天多少度
输出：{{"tool":"weather","arguments":{{"city":"成都"}}}}

用户：北京会下雨吗
输出：{{"tool":"weather","arguments":{{"city":"北京"}}}}

用户：上海热不热
输出：{{"tool":"weather","arguments":{{"city":"上海"}}}}

用户：你好
输出：{{"tool":null,"arguments":{{}}}}


用户输入：
{user_message}

你必须只输出 JSON，不要解释，不要 Markdown，不要代码块。

格式：
{{
  "tool": "weather",
  "arguments": {{
    "city": "北京"
  }}
}}

如果不需要工具，输出：
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