from collections.abc import Generator

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse

from app.models.chat import (
    ChatHistoryResponse,
    ChatRequest,
    ConversationCreateRequest,
    ConversationResponse,
    ConversationsResponse,
    ConversationUpdateRequest,
)
from app.services.agent import simple_agent
from app.services.memory import conversation_memory


router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


def stream_chat_response(
    conversation_id: int,
    messages: list[dict[str, str]],
) -> Generator[str, None, None]:
    chunks: list[str] = []

    for chunk in simple_agent(messages):
        chunks.append(chunk)
        yield chunk

    reply = "".join(chunks).strip()
    if reply:
        conversation_memory.add_message(conversation_id, "assistant", reply)


def require_conversation(conversation_id: int):
    conversation = conversation_memory.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    return conversation


@router.post("")
def chat(req: ChatRequest):
    conversation_id = req.conversation_id or conversation_memory.get_default_conversation_id()
    require_conversation(conversation_id)

    incoming_messages = [
        message.model_dump(exclude={"created_at"})
        for message in req.messages
    ]
    latest_message = incoming_messages[-1]

    conversation_memory.add_message(
        conversation_id,
        latest_message["role"],
        latest_message["content"],
    )
    messages = conversation_memory.get_messages(conversation_id)

    return StreamingResponse(
        stream_chat_response(conversation_id, messages),
        media_type="text/plain",
        headers={"X-Conversation-Id": str(conversation_id)},
    )


@router.get("/conversations", response_model=ConversationsResponse)
def list_conversations():
    return {
        "conversations": conversation_memory.list_conversations(),
    }


@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(req: ConversationCreateRequest | None = None):
    return {
        "conversation": conversation_memory.create_conversation(req.title if req else None),
    }


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
def update_conversation(conversation_id: int, req: ConversationUpdateRequest):
    conversation = conversation_memory.update_conversation_title(
        conversation_id,
        req.title,
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {
        "conversation": conversation,
    }


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int):
    if not conversation_memory.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="会话不存在")

    return Response(status_code=204)


@router.get("/conversations/{conversation_id}/history", response_model=ChatHistoryResponse)
def get_conversation_history(conversation_id: int):
    require_conversation(conversation_id)
    return {
        "messages": conversation_memory.get_history(conversation_id),
    }


@router.delete("/conversations/{conversation_id}/history", status_code=204)
def clear_conversation_history(conversation_id: int):
    require_conversation(conversation_id)
    conversation_memory.clear(conversation_id)
    return Response(status_code=204)


@router.get("/history", response_model=ChatHistoryResponse)
def get_chat_history():
    conversation_id = conversation_memory.get_default_conversation_id()
    return {
        "messages": conversation_memory.get_history(conversation_id),
    }


@router.delete("/history", status_code=204)
def clear_chat_history():
    conversation_id = conversation_memory.get_default_conversation_id()
    conversation_memory.clear(conversation_id)
    return Response(status_code=204)
