from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str
    created_at: str | None = None


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    messages: list[ChatMessage] = Field(min_length=1)


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessage]


class Conversation(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str


class ConversationCreateRequest(BaseModel):
    title: str | None = None


class ConversationUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)


class ConversationResponse(BaseModel):
    conversation: Conversation


class ConversationsResponse(BaseModel):
    conversations: list[Conversation]
