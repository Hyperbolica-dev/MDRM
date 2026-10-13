from threading import Event

import pandas as pd
import pytest

from model.record_storage import atomic_write_csv, record_revision
from ui.background_save import submit_sleep_save


def test_background_save_returns_before_calculation_and_preserves_concurrent_edit(tmp_path):
    path = tmp_path / "records.csv"
    original = pd.DataFrame({"value": [1]})
    atomic_write_csv(original, path, index=False)
    revision = record_revision(path)
    started, release = Event(), Event()

    def rebuild(records, params):
        started.set()
        assert release.wait(5)
        return None, None, None, records

    future = submit_sleep_save(pd.DataFrame({"value": [2]}), {}, path, revision, rebuild)
    try:
        assert started.wait(2)
        assert not future.done()
        atomic_write_csv(pd.DataFrame({"value": [3]}), path, index=False)
    finally:
        release.set()
    with pytest.raises(ValueError, match="Records changed"):
        future.result(timeout=5)
    assert pd.read_csv(path).value.tolist() == [3]


def test_failed_background_calculation_does_not_write(tmp_path):
    path = tmp_path / "records.csv"
    original = pd.DataFrame({"value": [1]})
    atomic_write_csv(original, path, index=False)
    before = path.read_bytes()

    def rebuild(records, params):
        raise ValueError("Invalid sleep")

    future = submit_sleep_save(original, {}, path, record_revision(path), rebuild)
    with pytest.raises(ValueError, match="Invalid sleep"):
        future.result(timeout=5)
    assert path.read_bytes() == before


def test_background_save_persists_snapshot(tmp_path):
    path = tmp_path / "records.csv"
    release = Event()
    frame = pd.DataFrame({"value": [1]})

    def rebuild(records, params):
        assert release.wait(5)
        return None, None, None, records

    future = submit_sleep_save(frame, {}, path, None, rebuild)
    frame.loc[0, "value"] = 9
    release.set()
    future.result(timeout=5)
    assert pd.read_csv(path).value.tolist() == [1]
