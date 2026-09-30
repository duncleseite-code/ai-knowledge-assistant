from app.services.chunking import chunk_text


def test_short_text_is_one_chunk():
    assert chunk_text("hello world", chunk_size=50, overlap=10) == ["hello world"]


def test_chunks_overlap_and_preserve_content():
    text = " ".join(f"word{i}" for i in range(100))
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert all(chunks)
