import pandas as pd

from scripts.align_mi_fitness_history import build_alignment


def test_authoritative_windows_correct_shifted_dates_and_preserve_uncovered_days():
    records = pd.DataFrame([
        dict(schema_version=2, date="2020-02-02", sleep_time="01:00", wake_time="08:00", momentum=7, disturbance=0, sleep_medication=False, awake_minutes=0, awake_unknown=False),
        dict(schema_version=2, date="2020-02-04", sleep_time="18:00", wake_time="22:00", momentum=4, disturbance=1, sleep_medication=True, awake_minutes=5, awake_unknown=False),
    ])
    windows = [("2020-02-03 18:00:00 +0800", "2020-02-03 22:00:00 +0800", "HKCategoryValueSleepAnalysisInBed")]
    aligned, dates, imported = build_alignment(records, windows)
    assert dates == ["2020-02-03", "2020-02-04"]
    assert aligned.date.tolist() == ["2020-02-02", "2020-02-03"]
    assert imported[0]["awake_minutes"] == 0
    assert imported[0]["momentum"] == 4
    assert imported[0]["sleep_medication"]


def test_new_source_day_uses_default_metadata_without_losing_columns():
    records = pd.DataFrame([dict(schema_version=2, date="2020-02-02", sleep_time="01:00", wake_time="08:00", momentum=7, disturbance=0, sleep_medication=False, awake_minutes=0, awake_unknown=False)])
    aligned, _, imported = build_alignment(records, [("2020-02-02 02:00:00 +0800", "2020-02-02 09:00:00 +0800", "HKCategoryValueSleepAnalysisInBed")])
    assert len(aligned) == 1
    assert imported[0]["sleep_time"] == "02:00"


def test_earlier_history_uses_defaults_and_retains_current_records():
    records = pd.DataFrame([dict(schema_version=2, date="2020-02-02", sleep_time="01:00", wake_time="08:00", momentum=7, disturbance=1, sleep_medication=True, awake_minutes=10, awake_unknown=False)])
    windows = [(f"{day} 01:00:00 +0800", f"{day} 08:00:00 +0800", "HKCategoryValueSleepAnalysisInBed") for day in ["2020-02-01", "2020-02-02"]]
    aligned, _, imported = build_alignment(records, windows, earlier_only=True)
    assert len(aligned) == 2
    assert len(imported) == 1
    assert imported[0]["momentum"] == 5
    assert imported[0]["disturbance"] == 0
    assert not imported[0]["sleep_medication"]
    assert aligned[aligned.date == "2020-02-02"].iloc[0].awake_minutes == 10
