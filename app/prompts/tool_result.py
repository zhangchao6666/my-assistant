from app.models.tool import ToolResult


def build_tool_result_prompt(
    user_message: str,
    tool_result: ToolResult,
) -> str:
    return f"""
用户问题：
{user_message}

工具名称：
{tool_result.tool_name}

工具结果：
{tool_result.content}

请根据工具结果回答用户。
要求：
1. 不要提到“工具结果”。
2. 不要编造工具中没有的信息。
3. 简洁自然。
"""