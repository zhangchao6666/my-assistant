import json
import re

from app.services.llm import LLM


def _extract_json(text: str) -> str | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    return match.group(0)


def build_plan(user_message: str) -> list[str]:
    llm = LLM()
    prompt = f"""
You are a task planner for an AI assistant.

Break the user's goal into 1-5 concise executable steps.
Do not answer the user's question.
Do not call tools.
Return JSON only.

Output format:
{{
  "steps": [
    "step 1",
    "step 2"
  ]
}}

User goal:
{user_message}
"""

    result = llm.chat(
        [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        use_tools=False,
    )
    json_text = _extract_json(result)
    if json_text is None:
        return []

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        return []

    steps = parsed.get("steps")
    if not isinstance(steps, list):
        return []

    return [
        str(step).strip()
        for step in steps[:5]
        if str(step).strip()
    ]
