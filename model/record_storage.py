import os
import shutil
import tempfile
from datetime import datetime


def keep_recent_record_backups(backup_dir, retention_count=30):
    if not os.path.exists(backup_dir):
        return
    backup_files = sorted(
        [
            os.path.join(backup_dir, name)
            for name in os.listdir(backup_dir)
            if name.startswith("records_backup_") and name.endswith(".csv")
        ],
        key=os.path.getmtime,
        reverse=True,
    )
    for path in backup_files[int(retention_count):]:
        try:
            os.remove(path)
        except OSError:
            pass


def create_record_backup(data_file, backup_dir, now=None, retention_count=30):
    if not os.path.exists(data_file):
        return None
    timestamp = now or datetime.now()
    os.makedirs(backup_dir, exist_ok=True)
    backup_name = timestamp.strftime("records_backup_%Y%m%d_%H%M%S_%f.csv")
    backup_path = os.path.join(backup_dir, backup_name)
    shutil.copy2(data_file, backup_path)
    keep_recent_record_backups(backup_dir, retention_count)
    return backup_path


def ensure_daily_record_backup(data_file, backup_dir, now=None, retention_count=30):
    if not os.path.exists(data_file):
        return None
    timestamp = now or datetime.now()
    today_prefix = timestamp.strftime("records_backup_%Y%m%d_")
    os.makedirs(backup_dir, exist_ok=True)
    if any(name.startswith(today_prefix) and name.endswith(".csv") for name in os.listdir(backup_dir)):
        return None
    return create_record_backup(data_file, backup_dir, timestamp, retention_count)


def atomic_write_csv(frame, path, **to_csv_kwargs):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(prefix=".records_", suffix=".csv", dir=directory)
    os.close(descriptor)
    try:
        frame.to_csv(temporary_path, **to_csv_kwargs)
        with open(temporary_path, "rb") as written_file:
            os.fsync(written_file.fileno())
        os.replace(temporary_path, path)
    except Exception:
        try:
            os.remove(temporary_path)
        except OSError:
            pass
        raise
