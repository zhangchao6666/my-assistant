from fastapi import FastAPI

from app.api.weather import router as weather_router
from app.api.chat import router as chat_router

app = FastAPI(
    title="My Assistant",
    description="个人 AI 助手后端服务",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "message": "Hello My Assistant"
    }

app.include_router(weather_router)
app.include_router(chat_router)