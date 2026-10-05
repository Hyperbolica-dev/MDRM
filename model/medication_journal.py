import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4


def read_medication_library(path):
    if not Path(path).exists():
        return []
    with sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True) as connection:
        return connection.execute("SELECT id, label FROM catalog ORDER BY label").fetchall()


def read_medication_journal(path):
    if not Path(path).exists():
        return []
    with sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True) as connection:
        return connection.execute("SELECT associated_day, label_snapshot, dose_text, time_text, note FROM journal ORDER BY associated_day DESC, created_at DESC LIMIT 100").fetchall()


def save_medication_event(path, event_id, associated_day, label, dose_text="", time_text="", note=""):
    label = label.strip()
    if not label:
        raise ValueError("请输入名称或代号 / Enter a name or alias")
    day = date.fromisoformat(str(associated_day))
    if day > date.today():
        raise ValueError("不能记录未来使用 / Future use cannot be logged")
    if time_text.strip():
        datetime.strptime(time_text.strip(), "%H:%M")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("CREATE TABLE IF NOT EXISTS catalog (id TEXT PRIMARY KEY, label TEXT NOT NULL UNIQUE)")
        connection.execute("CREATE TABLE IF NOT EXISTS journal (id TEXT PRIMARY KEY, catalog_id TEXT NOT NULL REFERENCES catalog(id), associated_day TEXT NOT NULL, label_snapshot TEXT NOT NULL, dose_text TEXT, time_text TEXT, note TEXT, created_at TEXT NOT NULL)")
        connection.execute("PRAGMA user_version=1")
        existing = connection.execute("SELECT associated_day, label_snapshot, dose_text, time_text, note FROM journal WHERE id=?", (event_id,)).fetchone()
        values = (day.isoformat(), label, dose_text.strip() or None, time_text.strip() or None, note.strip() or None)
        if existing is not None:
            if existing != values:
                raise ValueError("事件已保存，请新建记录 / Event already saved; start a new entry")
            return
        connection.execute("INSERT OR IGNORE INTO catalog (id, label) VALUES (?, ?)", (str(uuid4()), label))
        catalog_id = connection.execute("SELECT id FROM catalog WHERE label=?", (label,)).fetchone()[0]
        connection.execute("INSERT INTO journal VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (event_id, catalog_id, *values, datetime.now(timezone.utc).isoformat()))
