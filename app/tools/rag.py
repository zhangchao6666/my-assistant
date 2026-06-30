from app.services.rag import rag_store
from app.models.tool import ToolResult

def rag_tool(question: str):
    chunks = rag_store.search(question)
   
    if not rag_store.is_match(chunks):
        return ToolResult(
            matched=False,
            tool_name="rag",
            message="知识库未命中"
        )
    
    context = rag_store.build_context(question)
    
    return ToolResult(
        matched=True,
        tool_name="rag",
        content=context,
    )
        