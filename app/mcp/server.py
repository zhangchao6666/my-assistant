import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.tools.calculator import calculator_tool
from app.tools.weather import weather_tool


mcp = FastMCP("my-assistant-tools")


@mcp.tool()
def calculator(expression: str) -> str:
    """Calculate a basic arithmetic expression.

    Args:
        expression: Arithmetic expression using numbers and operators such as
            +, -, *, /, //, %, **, and parentheses.
    """
    result = calculator_tool(expression)
    if result.matched and result.content:
        return result.content

    return result.message or "The expression cannot be calculated."


@mcp.tool()
def weather(city: str) -> str:
    """Get the current weather for a city.

    Args:
        city: City name, such as Beijing, Shanghai, Chengdu, or New York.
    """
    result = weather_tool(city)
    if result.matched and result.content:
        return result.content

    return result.message or f"Could not fetch weather for {city}."


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
