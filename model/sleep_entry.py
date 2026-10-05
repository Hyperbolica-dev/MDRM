import re
import unicodedata

import pandas as pd

from model.dynamics import build_sleep_session
from model.time_input import normalize_clock_time


def parse_sleep_intervals(text, day):
    normalized = unicodedata.normalize("NFKC", text).strip()
    if not normalized:
        return pd.DataFrame(columns=["date", "sleep_time", "wake_time", "awake_minutes", "awake_unknown"])
    rows = []
    for interval in re.split(r"[;；\n]+", normalized):
        if not interval.strip():
            continue
        parts = re.split(r"\s*(?:-|–|—|→|至)\s*", interval.strip())
        if len(parts) != 2:
            raise ValueError("Use HH:MM-HH:MM; HH:MM-HH:MM")
        start, end = map(normalize_clock_time, parts)
        if start is None or end is None:
            raise ValueError("Invalid sleep interval")
        rows.append({"date": day, "sleep_time": start, "wake_time": end, "awake_minutes": 0, "awake_unknown": False})
    return pd.DataFrame(rows)


def validate_sleep_windows(frame, existing=None, allow_long=False):
    windows = []
    for row in frame.to_dict("records"):
        day = pd.Timestamp(row["date"]).date()
        start, end = build_sleep_session(day, row["sleep_time"], row["wake_time"])
        minutes = (end - start).total_seconds() / 60
        awake = float(row.get("awake_minutes", 0))
        if not 0 <= awake <= minutes:
            raise ValueError("清醒分钟必须在 0 与睡眠窗口长度之间 / Awake minutes exceed the window")
        if bool(row.get("awake_unknown", False)) and awake != 0:
            raise ValueError("清醒时长未知时请将清醒分钟设为 0 / Unknown awake time cannot include a known duration")
        if minutes <= 0:
            raise ValueError("零睡眠请使用通宵入口 / Use the no-sleep option for zero sleep")
        if minutes > 960 and not allow_long:
            raise ValueError("超过 16 小时请确认 / Confirm windows longer than 16 hours")
        if day > pd.Timestamp.today().date():
            raise ValueError("不能录入未来日期 / Future dates are not allowed")
        windows.append((start, end))
    existing_windows = []
    if existing is not None and not existing.empty:
        existing_windows = [build_sleep_session(pd.Timestamp(row["date"]).date(), row["sleep_time"], row["wake_time"]) for row in existing.to_dict("records")]
    for index, (start, end) in enumerate(windows):
        for other_start, other_end in windows[:index] + existing_windows:
            if start < other_end and end > other_start:
                raise ValueError("睡眠窗口重复或重叠，请核对 / Duplicate or overlapping sleep windows")
    return windows
