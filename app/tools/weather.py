from typing import Any

import requests

from app.models.tool import ToolResult


def get_weather(city: str) -> dict[str, Any] | None:
    """Fetch weather data for a city from wttr.in."""
    url = f"https://wttr.in/{city}?format=j1&lang=zh"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        print(f"Weather request failed: {exc}")
        return None
    except ValueError:
        print("Weather response could not be parsed as JSON.")
        return None


def format_weather(city: str, data: dict[str, Any]) -> str:
    current = data["current_condition"][0]
    description = current["weatherDesc"][0]["value"]
    temperature = current["temp_C"]
    feels_like = current.get("FeelsLikeC")

    lines = [
        f"City: {city}",
        f"Weather: {description}",
        f"Temperature: {temperature} C",
    ]
    if feels_like is not None:
        lines.append(f"Feels like: {feels_like} C")

    return "\n".join(lines)


def weather_tool(city: str | None) -> ToolResult:
    if not city:
        return ToolResult(
            matched=False,
            tool_name="weather",
            message="Missing city name.",
        )

    weather = get_weather(city)

    if weather is None:
        return ToolResult(
            matched=False,
            tool_name="weather",
            message=f"Could not fetch weather for {city}.",
        )

    return ToolResult(
        matched=True,
        tool_name="weather",
        content=format_weather(city, weather),
    )
