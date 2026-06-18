from fastapi import APIRouter

from app.models.chat import ChatRequest, ChatResponse
from app.services.llm import LLM


router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest):
    messages = [
        message.model_dump()
        for message in req.messages
    ]

    llm = LLM()
    reply = llm.chat(messages)

    return ChatResponse(reply=reply)