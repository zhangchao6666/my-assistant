import os

from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "My Assistant")
    app_description: str = os.getenv("APP_DESCRIPTION", "个人 AI 助手后端服务")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "lm-studio")
    chat_model: str = os.getenv("CHAT_MODEL", "qwen/qwen3.6-35b-a3b")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-mxbai-embed-large-v1")
    extractor_model: str = os.getenv("EXTRACTOR_MODEL", "qwen3.6")
    memory_db_path: str = os.getenv("MEMORY_DB_PATH", "data/chat_history.sqlite3")
    rag_chroma_path: str = os.getenv("RAG_CHROMA_PATH", "data/chroma")


settings = Settings()
