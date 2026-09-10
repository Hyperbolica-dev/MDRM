import math
from datetime import datetime, timedelta

import pandas as pd


def _format_clock(value: float) -> str:
    total_minutes = int(round(value * 60)) % (24 * 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def _normalize_clock(value: str) -> str:
    parsed = datetime.strptime(value, "%H:%M")
    return parsed.strftime("%H:%M")


def _candidate(action_type, rhythm_day, recommended_time, duration_minutes, reason_key, notes):
    return {
        "action_type": action_type,
        "rhythm_day": rhythm_day,
        "recommended_time": recommended_time,
        "recommended_duration_minutes": duration_minutes,
        "planned_time": "",
        "actual_time": "",
        "duration_minutes": "",
        "executed": False,
        "source": "mrdm_recommendation",
        "notes": notes,
        "reason_key": reason_key,
    }


def build_recommendation_candidates(
    current_state: dict,
    target_wake: str,
    sleep_need: float,
    rhythm_day=None,
    p_limit: float = 1.0,
    d_limit: float = 5.0,
    deadband: float = 0.5,
    cbt_min: float | None = None,
):
    target_wake = _normalize_clock(target_wake)
    rhythm_day = rhythm_day or datetime.now().date()
    p_value = current_state.get("P")
    d_value = current_state.get("D")
    p_valid = p_value is not None and pd.notna(p_value) and math.isfinite(float(p_value))
    d_valid = d_value is not None and pd.notna(d_value) and math.isfinite(float(d_value))

    if not p_valid:
        return [_candidate(
            "stabilize_wake",
            rhythm_day,
            target_wake,
            "",
            "recommendation_reason_data",
            "Keep the wake anchor while phase data is unavailable.",
        )]

    phase = float(p_value)
    if abs(phase) > 6.0:
        return [_candidate(
            "stabilize_wake",
            rhythm_day,
            target_wake,
            "",
            "recommendation_reason_phase_uncertain",
            "Keep the wake anchor and avoid intentional phase-shifting light.",
        )]

    if d_valid and float(d_value) >= float(d_limit):
        recovery_time = _format_clock((datetime.strptime(target_wake, "%H:%M").hour + datetime.strptime(target_wake, "%H:%M").minute / 60.0 - sleep_need) % 24.0)
        return [_candidate(
            "sleep_recovery",
            rhythm_day,
            recovery_time,
            "",
            "recommendation_reason_debt",
            "Prioritize a protected sleep opportunity before phase shifting.",
        )]

    if abs(phase) <= deadband:
        return [_candidate(
            "maintain_wake",
            rhythm_day,
            target_wake,
            "",
            "recommendation_reason_maintain",
            "Maintain the wake anchor and avoid unnecessary phase shifting.",
        )]

    if cbt_min is None or pd.isna(cbt_min):
        return [_candidate(
            "stabilize_wake",
            rhythm_day,
            target_wake,
            "",
            "recommendation_reason_data",
            "Keep the wake anchor until a usable CBT_min estimate is available.",
        )]

    scale = min(1.0, (abs(phase) - deadband) / 2.0)
    offset = 3.0 * scale
    light_hour = float(cbt_min) + offset if phase > 0 else float(cbt_min) - offset
    window_start = _format_clock(light_hour - 0.5)
    return [_candidate(
        "light",
        rhythm_day,
        window_start,
        30,
        "recommendation_reason_phase",
        f"Use a 30-minute light window beginning at {window_start}.",
    )]
