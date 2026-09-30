from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

from app.services.chunking import chunk_text


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1251"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def parse_document(filename: str, data: bytes) -> list[dict]:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext or 'unknown'}")

    records: list[dict] = []

    if ext == ".pdf":
        reader = PdfReader(BytesIO(data))
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            for chunk_index, chunk in enumerate(chunk_text(text), start=1):
                records.append(
                    {
                        "text": chunk,
                        "page": page_number,
                        "chunk": chunk_index,
                    }
                )
        return records

    text = _decode_text(data)
    for chunk_index, chunk in enumerate(chunk_text(text), start=1):
        records.append({"text": chunk, "page": None, "chunk": chunk_index})
    return records
