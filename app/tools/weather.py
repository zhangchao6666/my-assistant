from typing import Any

import requests

# from app.models.weather import WeatherResponse
from app.models.tool import ToolResult


def get_weather(city: str) -> dict[str, Any] | None:
    """查询指定城市的天气情况。"""
    url = f"https://wttr.in/{city}?format=j1&lang=zh"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"请求失败！错误信息: {e}")
        return None
    except ValueError:
        print("天气数据解析失败！")
        return None

    return data


def format_weather(city: str, data: dict[str, Any]) -> str:
    """格式化天气数据"""
    current = data["current_condition"][0]

    return f"""
    城市：{city}
    天气：{current["weatherDesc"][0]["value"]}
    温度：{current['temp_C']}
    """

def weather_tool(city: str | None) -> ToolResult:
    """天气查询工具入口。"""
    if not city:
        return ToolResult(
            matched=False,
            tool_name="weather",
            message="缺少城市名",
        )

    weather = get_weather(city)

    if weather is None:
        return ToolResult(
            matched=False,
            tool_name="weather",
            message=f"没有查询到{city}的天气",
        )

    return ToolResult(
        matched=True,
        tool_name="weather",
        content=format_weather(city, weather)
    )
