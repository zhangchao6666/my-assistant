from collections.abc import Generator

from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse

from app.models.chat import ChatHistoryResponse, ChatRequest
from app.services.agent import simple_agent
from app.services.memory import conversation_memory
from app.services.rag import rag_store


router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


def stream_chat_response(messages: list[dict[str, str]]) -> Generator[str, None, None]:
    chunks: list[str] = []

    for chunk in simple_agent(messages):
        chunks.append(chunk)
        yield chunk

    reply = "".join(chunks).strip()
    if reply:
        conversation_memory.add_message("assistant", reply)


@router.post("")
def chat(req: ChatRequest):
    incoming_messages = [
        message.model_dump(exclude={"created_at"})
        for message in req.messages
    ]
    latest_message = incoming_messages[-1]

    conversation_memory.add_message(
        latest_message["role"],
        latest_message["content"],
    )
    messages = conversation_memory.get_messages()
    rag_context = rag_store.build_context(latest_message["content"])
    if rag_context:
        messages = [
            *messages[:-1],
            {
                "role": "user",
                "content": (
                    "Use the following local reference snippets first. "
                    "If they are insufficient, say what is missing and then answer with general knowledge.\n\n"
                    f"{rag_context}\n\nUser question: {latest_message['content']}"
                ),
            },
        ]

    return StreamingResponse(
        stream_chat_response(messages),
        media_type="text/plain",
    )


@router.get("/history", response_model=ChatHistoryResponse)
def get_chat_history():
    return {
        "messages": conversation_memory.get_history(),
    }


@router.delete("/history", status_code=204)
def clear_chat_history():
    conversation_memory.clear()
    return Response(status_code=204)
