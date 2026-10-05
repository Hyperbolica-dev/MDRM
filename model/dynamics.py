import math
from datetime import date, datetime, timedelta

import pandas as pd
from model.time_input import normalize_clock_time

MAIN_SLEEP_THRESHOLD_HOURS = 3.0
EVENING_SLEEP_THRESHOLD = datetime.strptime("18:00", "%H:%M").time()
ROUTINE_WAKE_TAU_HOURS = 1.0


def parse_clock_time(time_str: str):
    normalized = normalize_clock_time(time_str)
    if normalized is None:
        raise ValueError("invalid clock time")
    return datetime.strptime(normalized, "%H:%M").time()


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
        window_hours = calculate_sleep_duration_hours(sleep_start, wake_end)
        awake_minutes = float(row.get("awake_minutes", 0))
        if not math.isfinite(awake_minutes) or not 0 <= awake_minutes <= window_hours * 60:
            raise ValueError("awake_minutes must fit the sleep window")
        if str(row.get("awake_unknown", False)).lower() in {"true", "1"} and awake_minutes != 0:
            raise ValueError("unknown awake time cannot include a known duration")
        sleep_hours.append(window_hours - awake_minutes / 60)
        rhythm_days.append(assign_rhythm_day(sleep_start, wake_end, wake_target_str))

    derived["sleep_start_dt"] = sleep_starts
    derived["wake_end_dt"] = wake_ends
    derived["sleep_hours"] = sleep_hours
    derived["rhythm_day"] = rhythm_days
    derived["is_main_sleep"] = derived["sleep_hours"] >= MAIN_SLEEP_THRESHOLD_HOURS
    derived["main_sleep_day"] = derived["rhythm_day"]
    derived["sleep_duration_known"] = ~derived.get("awake_unknown", pd.Series(False, index=derived.index)).fillna(False).map(lambda value: str(value).lower() in {"true", "1"})
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
    attractor_p_limit: float = 1.0,
    attractor_d_limit: float = 5.0,
    attractor_days: int = 7,
    routine_wake_tau_hours: float = ROUTINE_WAKE_TAU_HOURS,
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
        attractor_p_limit,
        attractor_d_limit,
        attractor_days,
        routine_wake_tau_hours,
    )

    if daily_summary.empty:
        return {
            "rhythm_day": None,
            "P": 0.0,
            "D": 0.0,
            "H": 1.0,
            "routine_stability": None,
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
    attractor_p_limit: float = 1.0,
    attractor_d_limit: float = 5.0,
    attractor_days: int = 7,
    routine_wake_tau_hours: float = ROUTINE_WAKE_TAU_HOURS,
):
    if derived.empty:
        return derived.copy()

    ordered = derived.sort_values(["wake_end_dt", "row_order"], ascending=[True, True]).copy()

    summary_rows = []
    first_day = min(ordered["main_sleep_day"])
    last_day = max(ordered["main_sleep_day"])
    distinct_days = [value.date() for value in pd.date_range(first_day, last_day, freq="D")]
    d_prev = 0.0
    h_prev = 1.0
    previous_wake_time = None
    qualifying_days = 0
    pending_disturbance_day = None
    state_estimated = False

    for rhythm_day in distinct_days:
        current_bucket = ordered[ordered["main_sleep_day"] == rhythm_day]
        total_sleep = float(current_bucket["sleep_hours"].sum())
        if not current_bucket.empty and not bool(current_bucket["sleep_duration_known"].all()):
            state_estimated = True
        disturbance_t = int(
            not current_bucket.empty
            and current_bucket["disturbance"].fillna(0).astype(bool).any()
        )
        if current_bucket.empty or total_sleep <= 0:
            p_t = None
            d_t = d_prev + sleep_need
            routine_stability_t = 0.0
            h_t = calculate_habit(h_prev, routine_stability_t, alpha_up, alpha_down)
            previous_wake_time = None
        else:
            main_sleep_bucket = current_bucket[current_bucket["is_main_sleep"]]
            if not main_sleep_bucket.empty:
                representative = main_sleep_bucket.sort_values(["sleep_hours", "row_order"], ascending=[False, False]).iloc[0]
            else:
                representative = current_bucket.sort_values(["sleep_hours", "row_order"], ascending=[False, False]).iloc[0]
            p_t = calculate_phase(representative["wake_time"], wake_target_str, sleep_need, total_sleep)
            d_t = calculate_sleep_debt(d_prev, total_sleep, sleep_need, lambda_d, recovery_k, recovery_saturation_tau)
            routine_stability_t = calculate_routine_stability(
                representative["wake_time"],
                previous_wake_time,
                routine_wake_tau_hours,
            )
            h_t = calculate_habit(h_prev, routine_stability_t, alpha_up, alpha_down)
            previous_wake_time = representative["wake_time"]

        if not state_estimated and check_attractor(p_t, d_t, attractor_p_limit, attractor_d_limit):
            qualifying_days += 1
        else:
            qualifying_days = 0
        in_attr = qualifying_days >= attractor_days

        if disturbance_t:
            pending_disturbance_day = rhythm_day
        recovery_days = None
        if pending_disturbance_day is not None and in_attr:
            recovery_days = (rhythm_day - pending_disturbance_day).days
            pending_disturbance_day = None

        summary_rows.append(
            {
                "rhythm_day": rhythm_day,
                "P": round(p_t, 2) if p_t is not None else None,
                "D": round(d_t, 2),
                "H": round(h_t, 3),
                "routine_stability": round(routine_stability_t, 3) if routine_stability_t is not None else None,
                "in_attractor": int(in_attr),
                "disturbance": disturbance_t,
                "recovery_days": recovery_days,
                "sleep_hours": round(total_sleep, 2),
                "session_count": int(len(current_bucket)),
                "observation_status": "missing_inferred" if current_bucket.empty else "reported_no_sleep" if total_sleep <= 0 else "reported_sleep",
                "sleep_duration_known": bool(not current_bucket.empty and current_bucket["sleep_duration_known"].all()),
                "state_estimated": state_estimated,
            }
        )

        d_prev = d_t
        h_prev = h_t

    summary_frame = pd.DataFrame(summary_rows)
    completed_recoveries = summary_frame[summary_frame["recovery_days"].notna()]
    for recovery_index, recovery_row in completed_recoveries.iterrows():
        prior_rows = summary_frame.loc[:recovery_index - 1]
        prior_disturbances = prior_rows[prior_rows["disturbance"].astype(bool)]
        if prior_disturbances.empty:
            continue
        disturbance_index = prior_disturbances.index[-1]
        summary_frame.loc[disturbance_index, "recovery_days"] = recovery_row["recovery_days"]
        summary_frame.loc[recovery_index, "recovery_days"] = None
    return summary_frame


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


def can_recommend_light(p_current: float | None) -> bool:
    return p_current is not None and not pd.isna(p_current) and abs(p_current) <= 6.0


def estimate_biological_utc_offset(p_values, target_utc_offset: float) -> float | None:
    valid_values = [float(value) for value in p_values if value is not None and not pd.isna(value)][-7:]
    if not valid_values:
        return None
    angles = [math.pi * value / 12.0 for value in valid_values]
    mean_sin = sum(math.sin(angle) for angle in angles) / len(angles)
    mean_cos = sum(math.cos(angle) for angle in angles) / len(angles)
    if math.hypot(mean_sin, mean_cos) < 1e-9:
        return None
    biological_phase = 12.0 * math.atan2(mean_sin, mean_cos) / math.pi
    utc_offset = target_utc_offset - biological_phase
    while utc_offset < -12.0:
        utc_offset += 24.0
    while utc_offset > 14.0:
        utc_offset -= 24.0
    return utc_offset


def calculate_live_state(
    last_wake: datetime | None,
    current_time: datetime,
    wake_target_str: str,
    sleep_need: float,
    formal_debt: float,
):
    if last_wake is None:
        return None
    next_target_wake = datetime.combine(last_wake.date() + timedelta(days=1), parse_clock_time(wake_target_str))
    expected_sleep_start = next_target_wake - timedelta(hours=sleep_need)
    assumed_awake_hours = max(0.0, (current_time - last_wake).total_seconds() / 3600.0)
    missed_sleep_hours = min(
        sleep_need,
        max(0.0, (current_time - expected_sleep_start).total_seconds() / 3600.0),
    )
    return {
        "current_time": current_time,
        "last_wake": last_wake,
        "expected_sleep_start": expected_sleep_start,
        "assumed_awake_hours": assumed_awake_hours,
        "missed_sleep_hours": missed_sleep_hours,
        "projected_debt": formal_debt + missed_sleep_hours,
    }


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


def calculate_routine_stability(
    wake_current_str: str | None,
    wake_previous_str: str | None,
    tau_hours: float = ROUTINE_WAKE_TAU_HOURS,
) -> float | None:
    if wake_current_str is None or wake_previous_str is None:
        return None
    if not math.isfinite(float(tau_hours)) or float(tau_hours) <= 0:
        raise ValueError("routine wake tau must be positive")
    current = parse_clock_time(wake_current_str)
    previous = parse_clock_time(wake_previous_str)
    current_minutes = current.hour * 60 + current.minute
    previous_minutes = previous.hour * 60 + previous.minute
    distance_minutes = abs(current_minutes - previous_minutes)
    distance_minutes = min(distance_minutes, 1440 - distance_minutes)
    return math.exp(-(distance_minutes / 60.0) / float(tau_hours))


def calculate_habit(
    h_prev: float,
    routine_stability: float | None,
    alpha_up: float,
    alpha_down: float,
) -> float:
    if routine_stability is None or pd.isna(routine_stability):
        return float(h_prev)
    routine_stability = min(max(float(routine_stability), 0.0), 1.0)
    if routine_stability >= h_prev:
        return alpha_up * h_prev + (1 - alpha_up) * routine_stability
    return alpha_down * h_prev + (1 - alpha_down) * routine_stability


def check_attractor(
    p_current: float | None,
    d_current: float,
    p_limit: float = 1.0,
    d_limit: float = 5.0,
) -> bool:
    return p_current is not None and abs(p_current) < p_limit and d_current < d_limit
