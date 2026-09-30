from __future__ import annotations

from pathlib import Path
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import UPLOAD_DIR, settings
from app.db import add_document, get_recent_messages, init_db, list_documents, list_notes, save_message
from app.schemas import AgentRequest, AskRequest, AskResponse, SourceItem
from app.services.document_service import SUPPORTED_EXTENSIONS, parse_document
from app.services.llm import local_llm
from app.services.rag import answer_question
from app.services.vector_store import vector_store


app = FastAPI(title=settings.app_name, version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()
    # Seamless v1 -> v2 migration: if the model-specific Nomic collection is empty,
    # rebuild it from files that were already uploaded in v1.
    if vector_store.collection.count() == 0:
        for doc in list_documents():
            matches = list(UPLOAD_DIR.glob(f"{doc['id']}_*"))
            if not matches:
                continue
            try:
                data = matches[0].read_bytes()
                chunks = parse_document(doc["filename"], data)
                if chunks:
                    vector_store.add_document(doc["id"], doc["filename"], chunks)
            except Exception as exc:
                print(f"Reindex skipped for {doc['filename']}: {exc}")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "indexed_chunks": vector_store.collection.count(),
    }


@app.get("/api/documents")
def documents() -> list[dict]:
    return list_documents()


@app.get("/api/notes")
def notes() -> list[dict]:
    return list_notes()


@app.post("/api/documents/upload")
async def upload_documents(files: list[UploadFile] = File(...)) -> dict:
    uploaded: list[dict] = []
    for file in files:
        filename = file.filename or "document"
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {filename}")

        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail=f"File is empty: {filename}")
        if len(data) > 25 * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"File is too large: {filename}")

        document_id = uuid.uuid4().hex
        safe_name = Path(filename).name
        (UPLOAD_DIR / f"{document_id}_{safe_name}").write_bytes(data)

        try:
            chunks = parse_document(safe_name, data)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to parse {safe_name}: {exc}") from exc
        if not chunks:
            raise HTTPException(status_code=400, detail=f"No text found in {safe_name}")

        vector_store.add_document(document_id, safe_name, chunks)
        add_document(document_id, safe_name, file.content_type, len(chunks))
        uploaded.append({"id": document_id, "filename": safe_name, "chunks": len(chunks)})

    return {"uploaded": uploaded}


@app.post("/api/ask", response_model=AskResponse)
def ask(payload: AskRequest) -> AskResponse:
    conversation_id = payload.conversation_id or uuid.uuid4().hex
    try:
        answer, chunks = answer_question(payload.question, conversation_id, payload.top_k)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LLM request failed: {exc}") from exc

    sources = [
        SourceItem(
            source=item["source"],
            page=item.get("page"),
            chunk=item.get("chunk"),
            distance=item.get("distance"),
            preview=item["text"][:220],
        )
        for item in chunks
    ]
    return AskResponse(conversation_id=conversation_id, answer=answer, sources=sources)


@app.get("/api/conversations/{conversation_id}")
def conversation(conversation_id: str) -> list[dict]:
    return get_recent_messages(conversation_id, limit=50)


@app.post("/api/agent")
def agent(payload: AgentRequest) -> dict:
    conversation_id = payload.conversation_id or uuid.uuid4().hex
    history = get_recent_messages(conversation_id, limit=8)
    save_message(conversation_id, "user", payload.message)
    try:
        answer = local_llm.agent(payload.message, history)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Agent request failed: {exc}") from exc
    save_message(conversation_id, "assistant", answer)
    return {"conversation_id": conversation_id, "answer": answer}
