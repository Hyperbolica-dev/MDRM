from datetime import datetime

import pandas as pd
import pytest

from model.record_storage import atomic_write_csv, ensure_daily_record_backup


def test_daily_backup_is_created_once_per_calendar_day(tmp_path):
    data_file = tmp_path / "records.csv"
    backup_dir = tmp_path / "backups"
    data_file.write_text("value\nfirst\n")

    first = ensure_daily_record_backup(
        str(data_file),
        str(backup_dir),
        datetime(2026, 9, 20, 8, 0),
    )
    duplicate = ensure_daily_record_backup(
        str(data_file),
        str(backup_dir),
        datetime(2026, 9, 20, 20, 0),
    )
    second_day = ensure_daily_record_backup(
        str(data_file),
        str(backup_dir),
        datetime(2026, 9, 21, 8, 0),
    )

    assert first is not None
    assert duplicate is None
    assert second_day is not None
    assert len(list(backup_dir.glob("records_backup_*.csv"))) == 2


def test_atomic_write_replaces_complete_file(tmp_path):
    path = tmp_path / "records.csv"
    path.write_text("value\nold\n")
    atomic_write_csv(pd.DataFrame({"value": ["new"]}), str(path), index=False)
    assert path.read_text() == "value\nnew\n"


def test_atomic_write_preserves_old_file_when_serialization_fails(tmp_path, monkeypatch):
    path = tmp_path / "records.csv"
    path.write_text("value\nold\n")

    def fail_to_csv(self, *args, **kwargs):
        raise RuntimeError("write failed")

    monkeypatch.setattr(pd.DataFrame, "to_csv", fail_to_csv)
    with pytest.raises(RuntimeError, match="write failed"):
        atomic_write_csv(pd.DataFrame({"value": ["new"]}), str(path), index=False)
    assert path.read_text() == "value\nold\n"
    assert not list(tmp_path.glob(".records_*.csv"))
