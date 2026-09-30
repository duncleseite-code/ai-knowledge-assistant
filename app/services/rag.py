from __future__ import annotations

from app.db import get_recent_messages, save_message
from app.services.llm import local_llm
from app.services.vector_store import vector_store
from app.config import settings


def build_context(chunks: list[dict]) -> str:
    blocks: list[str] = []
    for index, item in enumerate(chunks, start=1):
        location = item["source"]
        if item.get("page"):
            location += f", page {item['page']}"
        blocks.append(f"[{index}] {location}\n{item['text']}")
    return "\n\n".join(blocks)


def answer_question(question: str, conversation_id: str, top_k: int = settings.max_context_chunks) -> tuple[str, list[dict]]:
    chunks = vector_store.query(question, top_k=top_k)
    save_message(conversation_id, "user", question)

    if not chunks:
        answer = "База знаний пока пуста. Сначала загрузите PDF, TXT или Markdown-документ."
        save_message(conversation_id, "assistant", answer)
        return answer, []

    context = build_context(chunks)
    history = get_recent_messages(conversation_id, limit=8)[:-1]
    answer = local_llm.answer(question, context, history)
    save_message(conversation_id, "assistant", answer)
    return answer, chunks
