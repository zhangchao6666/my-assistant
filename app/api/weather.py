from fastapi import APIRouter

from app.models.weather import WeatherRequest, WeatherResponse
from app.tools.weather_tool import weather_tool


router = APIRouter(
    prefix="/weather",
    tags=["weather"]
)


@router.get(
    "",
    response_model=WeatherResponse,
    summary="查询天气 GET"
)
def get_weather_api(city: str):
    return weather_tool(city)


@router.post(
    "",
    response_model=WeatherResponse,
    summary="查询天气 POST"
)
def post_weather_api(req: WeatherRequest):
    return weather_tool(req.city)