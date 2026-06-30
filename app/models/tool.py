from pydantic import BaseModel

class ToolResult(BaseModel):
    matched: bool
    tool_name: str | None = None
    content: str | None = None
    message: str | None = None