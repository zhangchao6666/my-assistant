from pathlib import Path
from uuid import uuid4

import chromadb
from openai import OpenAI

from app.core.config import settings


class RagStore:
    def __init__(
        self,
        persist_path: str,  #chromadb 存储目录
        collection_name: str = "local_documents",
        chunk_size: int = 800,  #每个切片最多多少字符
        chunk_overlap: int = 120,  #相邻片段之间重叠多少字符
    ):
        self.persist_path = Path(persist_path)
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.persist_path.mkdir(parents=True, exist_ok=True)
        self.embedding_client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
        self.chroma_client = chromadb.PersistentClient(path=str(self.persist_path))
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_document(self, filename: str, content: str) -> dict[str, int | str]:
        text = content.strip()
        if not text:
            raise ValueError("uploaded file is empty")

        chunks = self._split_text(text)
        embeddings = self._embed(chunks)
        document_id = str(uuid4())
        ids = [f"{document_id}:{index}" for index in range(len(chunks))]
        metadatas = [
            {
                "document_id": document_id,
                "filename": filename,
                "chunk_index": index,
            }
            for index in range(len(chunks))
        ]

        self.collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        return {
            "document_id": document_id,
            "filename": filename,
            "chunks": len(chunks),
        }

    def search(self, query: str, limit: int = 3) -> list[dict[str, str | int | float]]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        query_embedding = self._embed([normalized_query])[0]
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        chunks = []
        for index, document in enumerate(documents):
            metadata = metadatas[index] or {}
            distance = distances[index]
            chunks.append(
                {
                    "chunk_id": int(metadata.get("chunk_index", index)),
                    "document_id": str(metadata.get("document_id", "")),
                    "filename": str(metadata.get("filename", "unknown")),
                    "content": document,
                    "score": 1 - float(distance),
                }
            )

        return chunks

    def build_context(self, query: str, limit: int = 3) -> str:
        chunks = self.search(query, limit=limit)
        if not chunks:
            return ""

        references = []
        for index, chunk in enumerate(chunks, start=1):
            references.append(
                f"[{index}] Source: {chunk['filename']}\n{chunk['content']}"
            )

        return "\n\n".join(references)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        response = self.embedding_client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def _split_text(self, text: str) -> list[str]:
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end].strip())
            if end >= len(text):
                break
            start = max(end - self.chunk_overlap, start + 1)
        return [chunk for chunk in chunks if chunk]


rag_store = RagStore(
    persist_path=settings.rag_chroma_path,
)