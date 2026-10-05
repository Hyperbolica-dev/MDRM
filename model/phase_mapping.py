import cmath
import math

import pandas as pd

from model.dynamics import calculate_phase, parse_clock_time


def wrap_phase_hours(value):
    return (value + 12) % 24 - 12


def clock_hours(value):
    timestamp = pd.Timestamp(value)
    return timestamp.hour + timestamp.minute / 60 + timestamp.second / 3600


def compare_phase_mapping(bucket, target_wake, sleep_need):
    result = {"legacy_error": None, "main_error": None, "main_halfwidth": None, "circular_error": None, "concentration": None, "status": "no_sleep"}
    ordered = bucket.sort_values("sleep_start_dt")
    intervals = []
    for row in ordered.to_dict("records"):
        start, end = pd.Timestamp(row["sleep_start_dt"]), pd.Timestamp(row["wake_end_dt"])
        if end <= start:
            continue
        if intervals and start < intervals[-1][1]:
            return {**result, "status": "overlap"}
        if not row["sleep_duration_known"]:
            return {**result, "status": "unknown_duration"}
        window = (end - start).total_seconds() / 3600
        sleep = float(row["sleep_hours"])
        if not math.isfinite(sleep) or not 0 <= sleep <= window:
            return {**result, "status": "invalid_duration"}
        intervals.append((start, end, sleep, window - sleep))
    if not intervals or sum(item[2] for item in intervals) <= 0:
        return result
    positive = ordered[ordered["sleep_hours"] > 0]
    representative = positive.sort_values(["sleep_hours", "row_order"], ascending=[False,False]).iloc[0]
    total_sleep = sum(item[2] for item in intervals)
    result["legacy_error"] = calculate_phase(representative["wake_time"], target_wake, sleep_need, total_sleep)
    wake = parse_clock_time(target_wake)
    target = wake.hour + wake.minute/60 - sleep_need/2
    merged = []
    for start, end, sleep, awake in intervals:
        if merged and start == merged[-1][1] and abs(awake) < 1e-9 and abs(merged[-1][3]) < 1e-9:
            previous = merged.pop()
            merged.append((previous[0],end,previous[2]+sleep,0))
        else:
            merged.append((start,end,sleep,awake))
    dominant = max(merged, key=lambda item: item[2])
    if dominant[2] >= 3 and dominant[2] > total_sleep/2:
        midpoint = dominant[0] + (dominant[1]-dominant[0])/2
        result.update(main_error=wrap_phase_hours(clock_hours(midpoint)-target), main_halfwidth=dominant[3]/2, status="dominant_window")
    else:
        result["status"] = "no_dominant_window"
    if all(abs(item[3]) < 1e-9 for item in intervals):
        omega = math.pi/12
        vector = 0j
        total = 0
        for start, end, sleep, awake in intervals:
            hours = (end-start).total_seconds()/3600
            a, b = clock_hours(start), clock_hours(start)+hours
            vector += (cmath.exp(1j*omega*b)-cmath.exp(1j*omega*a))/(1j*omega)
            total += hours
        vector /= total
        concentration = abs(vector)
        result["concentration"] = concentration
        if concentration > 1e-8:
            result["circular_error"] = wrap_phase_hours(cmath.phase(vector)/omega-target)
    return result


def build_phase_mapping_frame(sessions, target_wake, sleep_need):
    rows = [{"rhythm_day": day, **compare_phase_mapping(bucket, target_wake, sleep_need)} for day, bucket in sessions.groupby("main_sleep_day", sort=True)] if not sessions.empty else []
    return pd.DataFrame(rows, columns=["rhythm_day","legacy_error","main_error","main_halfwidth","circular_error","concentration","status"])
