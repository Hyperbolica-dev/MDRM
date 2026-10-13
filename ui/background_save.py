from concurrent.futures import ThreadPoolExecutor

from model.record_storage import atomic_write_csv


_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="sleep-save")


def submit_sleep_save(records, params, path, revision, rebuild):
    return _executor.submit(_save, records.copy(deep=True), dict(params), path, revision, rebuild)


def _save(records, params, path, revision, rebuild):
    _, _, _, persisted = rebuild(records, params)
    atomic_write_csv(persisted, path, expected_revision=revision, index=False)
