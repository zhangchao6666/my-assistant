from app.models.tool import ToolResult
from app.models.planner import ToolDecision

from app.tools.calculator import calculator_tool
from app.tools.weather import weather_tool

def execute_tool(decision: ToolDecision) -> ToolResult:
    if decision.tool == "weather":
        city = decision.arguments.get("city")
        return weather_tool(city)

    if decision.tool == "caluclator":
        expression = decision.arguments.get("expression")
        return calculator_tool(expression)
    
    return ToolResult(
        matched=False,
        tool_name=decision.tool or "none",
        message="没有匹配到可用工具",
    )
    