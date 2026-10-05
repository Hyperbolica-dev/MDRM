import sqlite3
from datetime import date

import pytest

from model.medication_journal import read_medication_journal, read_medication_library, save_medication_event


def test_optional_storage_is_lazy_and_events_are_idempotent(tmp_path):
    path = tmp_path / "private" / "medication.sqlite3"
    assert read_medication_library(path) == []
    assert read_medication_journal(path) == []
    assert not path.exists()
    save_medication_event(path, "event", date.today(), "Alias A")
    save_medication_event(path, "event", date.today(), "Alias A")
    assert len(read_medication_library(path)) == 1
    assert read_medication_journal(path) == [(date.today().isoformat(), "Alias A", None, None, None)]
    with pytest.raises(ValueError):
        save_medication_event(path, "event", date.today(), "Alias B")
    assert len(read_medication_library(path)) == 1


def test_optional_fields_roundtrip_and_bad_input_does_not_create_database(tmp_path):
    path = tmp_path / "medication.sqlite3"
    with pytest.raises(ValueError):
        save_medication_event(path, "bad", date.today(), "A", time_text="29:00")
    assert not path.exists()
    save_medication_event(path, "one", date.today(), "A", "half a tablet", "23:15", "optional")
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
    assert read_medication_journal(path)[0][1:] == ("A", "half a tablet", "23:15", "optional")
