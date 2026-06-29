from fastapi import FastAPI

from app.api.routes.chat import router as chat_router
from app.api.routes.rag import router as rag_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)


@app.get("/")
def root():
    return {
        "message": "Hello My Assistant",
    }


app.include_router(chat_router)
app.include_router(rag_router)
