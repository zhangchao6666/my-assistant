from app.models.tool import ToolResult


def build_tool_result_prompt(
    user_message: str,
    tool_result: ToolResult,
) -> str:
    return f"""
User question:
{user_message}

Tool name:
{tool_result.tool_name}

Tool result:
{tool_result.content or tool_result.message or ""}

Answer the user based on the tool result.
Requirements:
1. Do not mention the phrase "tool result".
2. Do not invent information that is not present above.
3. Keep the answer concise and natural.
"""
