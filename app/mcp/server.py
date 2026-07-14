import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.tools.calculator import calculator_tool
from app.tools.rag import rag_tool
from app.tools.weather import weather_tool


mcp = FastMCP("my-assistant-tools")


@mcp.tool()
def calculator(expression: str) -> str:
    """Use this tool for any math or arithmetic question.

    Call this tool when the user asks about calculations such as addition,
    subtraction, multiplication, division, powers, squares, square roots,
    percentages, equations, or numeric comparison. Convert natural language math
    into a Python-style arithmetic expression, for example: "18 的平方" ->
    "18 ** 2".

    Args:
        expression: Python-style arithmetic expression using numbers and
            operators such as +, -, *, /, //, %, **, and parentheses.
    """
    result = calculator_tool(expression)
    if result.matched and result.content:
        return result.content

    return result.message or "The expression cannot be calculated."


@mcp.tool()
def weather(city: str) -> str:
    """Use this tool for current weather and temperature questions.

    Call this tool for real-time weather, current temperature, rain, heat/cold,
    or comparing weather/temperature between cities.

    Args:
        city: City name, such as 北京, 上海, 成都, 乐山, Beijing, or New York.
    """
    result = weather_tool(city)
    if result.matched and result.content:
        return result.content

    return result.message or f"Could not fetch weather for {city}."


@mcp.tool()
def rag(query: str) -> str:
    """Use this tool to retrieve information from the local knowledge base.

    Call this tool only for questions about stored documents, project notes,
    local knowledge base content, or previously indexed materials. Do not use it
    for real-time weather or arithmetic.

    Args:
        query: The query string to search in the knowledge base.
    """
    result = rag_tool(query)
    if result.matched and result.content:
        return result.content

    return result.message or f"No relevant information found for '{query}'."


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
