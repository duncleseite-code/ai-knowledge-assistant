from pathlib import Path

import app.db as db


def test_save_and_list_notes(tmp_path: Path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db()

    saved = db.save_note("Test", "Function calling note")
    notes = db.list_notes()

    assert saved["title"] == "Test"
    assert len(notes) == 1
    assert notes[0]["content"] == "Function calling note"
