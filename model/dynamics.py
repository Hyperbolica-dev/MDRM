import math
from datetime import date, datetime, timedelta

import pandas as pd

MAIN_SLEEP_THRESHOLD_HOURS = 3.0
EVENING_SLEEP_THRESHOLD = datetime.strptime("18:00", "%H:%M").time()


def parse_clock_time(time_str: str):
    return datetime.strptime(time_str, "%H:%M").time()


def build_sleep_session(session_date: date, sleep_start_str: str, wake_end_str: str):
    sleep_start = datetime.combine(session_date, parse_clock_time(sleep_start_str))
    wake_end = datetime.combine(session_date, parse_clock_time(wake_end_str))

    if sleep_start > wake_end:
        sleep_start -= timedelta(days=1)

    return sleep_start, wake_end


def calculate_sleep_duration_hours(sleep_start: datetime, wake_end: datetime) -> float:
    return (wake_end - sleep_start).total_seconds() / 3600.0


def assign_rhythm_day(sleep_start: datetime, wake_end: datetime, wake_target_str: str) -> date:
    _ = wake_target_str
    if wake_end.date() > sleep_start.date():
        return wake_end.date()
    if sleep_start.time() >= EVENING_SLEEP_THRESHOLD:
        return wake_end.date() + timedelta(days=1)
    return wake_end.date()


def derive_session_frame(df, wake_target_str: str):
    if df.empty:
        return df.copy()

    derived = df.copy()
    derived["date"] = pd.to_datetime(derived["date"]).dt.date
    derived["row_order"] = range(len(derived))
    sleep_starts = []
    wake_ends = []
    sleep_hours = []
    rhythm_days = []

    for _, row in derived.iterrows():
        sleep_start, wake_end = build_sleep_session(row["date"], row["sleep_time"], row["wake_time"])
        sleep_starts.append(sleep_start)
        wake_ends.append(wake_end)
        sleep_hours.append(calculate_sleep_duration_hours(sleep_start, wake_end))
        rhythm_days.append(assign_rhythm_day(sleep_start, wake_end, wake_target_str))

    derived["sleep_start_dt"] = sleep_starts
    derived["wake_end_dt"] = wake_ends
    derived["sleep_hours"] = sleep_hours
    derived["rhythm_day"] = rhythm_days
    derived["is_main_sleep"] = derived["sleep_hours"] >= MAIN_SLEEP_THRESHOLD_HOURS
    derived["main_sleep_day"] = derived["rhythm_day"]
    return derived


def calculate_daily_state(
    df,
    wake_target_str: str,
    sleep_need: float,
    lambda_d: float,
    alpha_up: float,
    alpha_down: float,
    recovery_k: float = 0.4,
    recovery_saturation_tau: float = 2.0,
):
    derived = derive_session_frame(df, wake_target_str)
    daily_summary = build_daily_summary_frame(
        derived,
        wake_target_str,
        sleep_need,
        lambda_d,
        alpha_up,
        alpha_down,
        recovery_k,
        recovery_saturation_tau,
    )

    if daily_summary.empty:
        return {
            "rhythm_day": None,
            "P": 0.0,
            "D": 0.0,
            "H": 1.0,
            "in_attractor": 0,
            "sleep_hours": 0.0,
            "session_count": 0,
        }, derived

    return daily_summary.iloc[-1].to_dict(), derived


def build_daily_summary_frame(
    derived,
    wake_target_str: str,
    sleep_need: float,
    lambda_d: float,
    alpha_up: float,
    alpha_down: float,
    recovery_k: float = 0.4,
    recovery_saturation_tau: float = 2.0,
):
    if derived.empty:
        return derived.copy()

    ordered = derived.sort_values(["wake_end_dt", "row_order"], ascending=[True, True]).copy()

    summary_rows = []
    distinct_days = list(dict.fromkeys(ordered["main_sleep_day"].tolist()))
    d_prev = 0.0
    h_prev = 1.0

    for rhythm_day in distinct_days:
        current_bucket = ordered[ordered["main_sleep_day"] == rhythm_day]
        total_sleep = float(current_bucket["sleep_hours"].sum())
        if total_sleep <= 0:
            p_t = None
            d_t = calculate_sleep_debt(d_prev, total_sleep, sleep_need, lambda_d, recovery_k, recovery_saturation_tau)
            h_t = alpha_down * h_prev
            in_attr = 0
        else:
            main_sleep_bucket = current_bucket[current_bucket["is_main_sleep"]]
            if not main_sleep_bucket.empty:
                representative = main_sleep_bucket.sort_values(["sleep_hours", "row_order"], ascending=[False, False]).iloc[0]
            else:
                representative = current_bucket.sort_values(["sleep_hours", "row_order"], ascending=[False, False]).iloc[0]
            p_t = calculate_phase(representative["wake_time"], wake_target_str, sleep_need, total_sleep)
            d_t = calculate_sleep_debt(d_prev, total_sleep, sleep_need, lambda_d, recovery_k, recovery_saturation_tau)
            h_t = calculate_habit(h_prev, p_t, alpha_up, alpha_down)
            in_attr = check_attractor(p_t, d_t)

        summary_rows.append(
            {
                "rhythm_day": rhythm_day,
                "P": round(p_t, 2) if p_t is not None else None,
                "D": round(d_t, 2),
                "H": round(h_t, 3),
                "in_attractor": int(in_attr),
                "sleep_hours": round(total_sleep, 2),
                "session_count": int(len(current_bucket)),
            }
        )

        d_prev = d_t
        h_prev = h_t

    return pd.DataFrame(summary_rows)


def calculate_phase(wake_actual_str, wake_target_str, sleep_need, total_sleep):
    fmt = "%H:%M"
    wake_actual = datetime.strptime(wake_actual_str, fmt)
    wake_target = datetime.strptime(wake_target_str, fmt)

    wa_hours = wake_actual.hour + wake_actual.minute / 60.0
    wt_hours = wake_target.hour + wake_target.minute / 60.0

    m_actual = wa_hours - total_sleep / 2.0
    m_target = wt_hours - sleep_need / 2.0

    diff = m_actual - m_target

    if diff > 12: diff -= 24
    elif diff < -12: diff += 24

    return diff


def estimate_cbt_min(wake_actual_str: str, total_sleep: float) -> float:
    fmt = "%H:%M"
    wake_actual = datetime.strptime(wake_actual_str, fmt)
    wa_hours = wake_actual.hour + wake_actual.minute / 60.0
    msm = wa_hours - total_sleep / 2.0
    cbt_min = msm + 1.5
    if cbt_min > 12:
        cbt_min -= 24
    elif cbt_min < -12:
        cbt_min += 24
    return cbt_min


def prc_shift(cbt_min: float, light_hour: float, lux: float = 10000.0) -> float:
    phase_angle = light_hour - cbt_min
    while phase_angle > 12:
        phase_angle -= 24
    while phase_angle < -12:
        phase_angle += 24

    amplitude = min(1.2, 1.2 * lux / 10000.0)

    if phase_angle < -6.0 or phase_angle > 6.0:
        return 0.0
    return -amplitude * math.sin(math.pi * phase_angle / 6.0)


def calculate_sleep_debt(
    d_prev: float,
    sleep_actual: float,
    sleep_need: float,
    lambda_d: float,
    recovery_k: float = 0.4,
    recovery_saturation_tau: float = 2.0,
) -> float:
    excess = sleep_actual - sleep_need
    if excess <= 0:
        return max(0, lambda_d * d_prev - excess)
    saturated_recovery = d_prev * recovery_k * (1 - math.exp(-excess / recovery_saturation_tau))
    return max(0, lambda_d * d_prev - saturated_recovery)


def calculate_habit(h_prev: float, p_current: float, alpha_up: float, alpha_down: float) -> float:
    if abs(p_current) < 1.0:
        return alpha_up * h_prev + (1 - alpha_up)
    else:
        return alpha_down * h_prev


def check_attractor(p_current: float, d_current: float) -> bool:
    return abs(p_current) < 1.0 and d_current < 5.0