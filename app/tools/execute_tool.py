from app.mcp.client import call_mcp_tool
from app.models.planner import ToolDecision
from app.models.tool import ToolResult


MCP_TOOLS = {"calculator", "weather"}


def execute_tool(decision: ToolDecision) -> ToolResult:
    if decision.tool in MCP_TOOLS:
        try:
            content = call_mcp_tool(decision.tool, decision.arguments)
        except Exception as exc:
            return ToolResult(
                matched=False,
                tool_name=decision.tool,
                message=f"MCP {decision.tool} call failed: {exc}",
            )

        return ToolResult(
            matched=True,
            tool_name=decision.tool,
            content=content,
        )

    return ToolResult(
        matched=False,
        tool_name=decision.tool or "none",
        message="No matching tool is available.",
    )
