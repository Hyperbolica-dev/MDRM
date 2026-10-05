import math

import pandas as pd


def advance_sleep_pressure(value, hours, asleep):
    if not math.isfinite(value) or not 0 <= value <= 1 or not math.isfinite(hours) or hours < 0:
        raise ValueError("Pressure and elapsed hours must be finite and in range")
    return value * math.exp(-hours / 4.2) if asleep else 1 - (1 - value) * math.exp(-hours / 18.2)


def build_sleep_pressure_frame(sessions, daily_summary):
    rows = []
    lower, upper = 0.0, 1.0
    previous_end = None
    previous_day = None
    for day in sorted(daily_summary["rhythm_day"].tolist()) if not daily_summary.empty else []:
        bucket = sessions[sessions["main_sleep_day"] == day].sort_values("sleep_start_dt")
        row = {"rhythm_day": day, "S_low": None, "S_high": None, "S": None, "pressure_at": None}
        if bucket.empty or bucket["sleep_hours"].sum() <= 0:
            lower, upper, previous_end, previous_day = 0.0, 1.0, None, None
            rows.append(row)
            continue
        if previous_day is None or (pd.Timestamp(day) - pd.Timestamp(previous_day)).days != 1:
            lower, upper, previous_end = 0.0, 1.0, None
        valid = True
        for item in bucket.to_dict("records"):
            start, end = pd.Timestamp(item["sleep_start_dt"]), pd.Timestamp(item["wake_end_dt"])
            window = (end - start).total_seconds() / 3600
            if window == 0:
                continue
            if previous_end is not None:
                gap = (start - previous_end).total_seconds() / 3600
                if gap < 0:
                    valid = False
                    break
                lower = advance_sleep_pressure(lower, gap, False)
                upper = advance_sleep_pressure(upper, gap, False)
            if not item["sleep_duration_known"]:
                lower = advance_sleep_pressure(lower, window, True)
                upper = advance_sleep_pressure(upper, window, False)
            else:
                sleep = float(item["sleep_hours"])
                awake = max(0.0, window - sleep)
                lower = advance_sleep_pressure(advance_sleep_pressure(lower, awake, False), sleep, True)
                upper = advance_sleep_pressure(advance_sleep_pressure(upper, sleep, True), awake, False)
            previous_end = end
        if valid:
            row.update(S_low=100 * lower, S_high=100 * upper, S=50 * (lower + upper), pressure_at=previous_end)
            previous_day = day
        else:
            lower, upper, previous_end, previous_day = 0.0, 1.0, None, None
        rows.append(row)
    return pd.DataFrame(rows, columns=["rhythm_day", "S_low", "S_high", "S", "pressure_at"])
