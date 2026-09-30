from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma"
DB_PATH = DATA_DIR / "app.db"

load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI Knowledge Assistant"
    lm_studio_base_url: str = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    lm_studio_api_key: str = os.getenv("LM_STUDIO_API_KEY", "lm-studio")
    # Explicit model IDs prevent the chat client from accidentally selecting the embedding model.
    lm_studio_model: str = (os.getenv("LM_STUDIO_MODEL", "").strip() or "google/gemma-4-e4b")
    embedding_model: str = (
        os.getenv("EMBEDDING_MODEL", "").strip() or "text-embedding-nomic-embed-text-v1.5"
    )
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "knowledge_base")
    max_context_chunks: int = int(os.getenv("MAX_CONTEXT_CHUNKS", "3"))
    min_relevance: float = float(os.getenv("MIN_RELEVANCE", "0.15"))


settings = Settings()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
