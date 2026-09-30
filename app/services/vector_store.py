from __future__ import annotations

import re

import chromadb
from openai import OpenAI

from app.config import CHROMA_DIR, settings


def _collection_suffix(model_id: str) -> str:
    """Create a stable Chroma-safe suffix from the embedding model id."""
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", model_id).strip("_")
    return value[-48:] or "embeddings"


class VectorStore:
    def __init__(self) -> None:
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.embedding_client = OpenAI(
            base_url=settings.lm_studio_base_url,
            api_key=settings.lm_studio_api_key,
        )
        # A model-specific collection avoids dimension conflicts when switching embedding models.
        collection_name = f"{settings.chroma_collection}_{_collection_suffix(settings.embedding_model)}"
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine", "embedding_model": settings.embedding_model},
        )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.embedding_client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]

    def add_document(self, document_id: str, filename: str, chunks: list[dict]) -> None:
        ids = [f"{document_id}:{i}" for i in range(len(chunks))]
        documents = [item["text"] for item in chunks]
        metadatas = [
            {
                "document_id": document_id,
                "source": filename,
                "page": item["page"] if item["page"] is not None else -1,
                "chunk": item["chunk"],
            }
            for item in chunks
        ]
        if ids:
            embeddings = self._embed(documents)
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )

    def query(self, question: str, top_k: int = 3) -> list[dict]:
        if self.collection.count() == 0:
            return []
        query_embedding = self._embed([question])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        docs = (results.get("documents") or [[]])[0]
        metas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        output: list[dict] = []
        for doc, meta, distance in zip(docs, metas, distances):
            output.append(
                {
                    "text": doc,
                    "source": meta.get("source", "unknown"),
                    "page": None if meta.get("page", -1) == -1 else meta.get("page"),
                    "chunk": meta.get("chunk"),
                    "distance": float(distance) if distance is not None else None,
                }
            )
        return output


vector_store = VectorStore()
