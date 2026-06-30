from app.models.tool import ToolResult

def calculator_tool(expression: str | None) -> ToolResult:
    if not expression:
        return ToolResult(
            matched=False,
            tool_name="calculator",
            message="缺少计算表达式",
        )

    try:
        result = eval(expression, {"__builtins__": {}}, {})

    except Exception:
        return ToolResult(
            matched=False,
            tool_name="calculator",
            message="表达式无法计算",
        )

    return ToolResult(
        matched=True,
        tool_name="calculator",
        content=f"{expression} = {result}"
    )