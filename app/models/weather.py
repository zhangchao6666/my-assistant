from pydantic import BaseModel, Field

class WeatherResponse(BaseModel):
    city: str
    weather: str
    temp: str

class WeatherRequest(BaseModel):
    city: str = Field(min_length=1, description="城市名称")