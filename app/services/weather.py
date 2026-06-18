import requests
from typing import Any

from app.models.weather import WeatherResponse

def get_weather(city: str) -> dict[str, Any] | None:
    """查询指定城市的天气情况"""
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
    else:
        return data
    
def format_weather(city: str, data: dict) -> WeatherResponse:
    """天气数据格式化"""
    current = data["current_condition"][0]
    return WeatherResponse(
        city=city,
        weather=current["weatherDesc"][0]["value"],
        temp=f"{current['temp_C']} ℃"
    )