from app.models.weather import WeatherResponse
from app.services.weather import get_weather, format_weather

def weather_tool(city: str) -> WeatherResponse | None:
    """天气查询工具入口"""
    data = get_weather(city)
    if data is None:
        return None
    return format_weather(city, data)