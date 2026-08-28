import math
from datetime import date, datetime

import pandas as pd
import pytest

from model.dynamics import (
    assign_rhythm_day,
    build_daily_summary_frame,
    build_sleep_session,
    calculate_live_state,
    calculate_phase,
    calculate_sleep_debt,
    can_recommend_light,
    derive_session_frame,
    estimate_cbt_min,
    estimate_biological_utc_offset,
)


def records(rows):
    return pd.DataFrame(
        [
            {
                "date": day,
                "sleep_time": sleep,
                "wake_time": wake,
                "momentum": 5,
                "disturbance": 0,
                "sleep_medication": False,
            }
            for day, sleep, wake in rows
        ]
    )


def summarize(rows, p_limit=1.0, d_limit=5.0, attractor_days=7):
    derived = derive_session_frame(records(rows), "08:30")
    return build_daily_summary_frame(
        derived, "08:30", 7.0, 0.9, 0.98, 0.5, 0.4, 2.0,
        p_limit, d_limit, attractor_days,
    )


def test_rhythm_day_uses_fixed_evening_boundary_and_wake_date():
    day = date(2026, 8, 1)
    before_start, before_end = build_sleep_session(day, "17:59", "19:00")
    evening_start, evening_end = build_sleep_session(day, "18:00", "20:00")
    overnight_start, overnight_end = build_sleep_session(day, "23:00", "07:00")
    assert assign_rhythm_day(before_start, before_end, "08:30") == day
    assert assign_rhythm_day(evening_start, evening_end, "08:30") == date(2026, 8, 2)
    assert assign_rhythm_day(overnight_start, overnight_end, "08:30") == day


def test_phase_and_cbt_min_use_total_rhythm_day_sleep():
    summary = summarize([
        ("2026-08-01", "02:00", "08:00"),
        ("2026-08-01", "12:00", "14:00"),
    ])
    assert summary.iloc[0]["sleep_hours"] == 8.0
    assert summary.iloc[0]["P"] == -1.0
    assert calculate_phase("08:00", "08:30", 7.0, 8.0) == -1.0
    assert estimate_cbt_min("08:00", 8.0) == 5.5


def test_sleep_debt_recovery_is_proportional_and_saturated():
    result = calculate_sleep_debt(10.0, 9.0, 7.0, 0.9, 0.4, 2.0)
    assert result == pytest.approx(9.0 - 4.0 * (1.0 - math.exp(-1.0)))


def test_explicit_zero_sleep_marks_phase_undefined_and_decays_habit():
    summary = summarize([("2026-08-01", "08:00", "08:00")])
    assert pd.isna(summary.iloc[0]["P"])
    assert summary.iloc[0]["D"] == 7.0
    assert summary.iloc[0]["H"] == 0.5


def test_internal_missing_days_are_all_nighters_without_trailing_inference():
    summary = summarize([
        ("2026-08-01", "01:30", "08:30"),
        ("2026-08-03", "01:30", "08:30"),
    ])
    assert summary["rhythm_day"].tolist() == [date(2026, 8, 1), date(2026, 8, 2), date(2026, 8, 3)]
    missing = summary.iloc[1]
    assert pd.isna(missing["P"])
    assert missing["D"] == 7.0
    assert missing["H"] == 0.5
    assert summary.iloc[-1]["rhythm_day"] == date(2026, 8, 3)


def test_consecutive_all_nighters_add_full_sleep_need_without_debt_decay():
    summary = summarize([
        ("2026-08-01", "08:00", "08:00"),
        ("2026-08-02", "08:00", "08:00"),
    ])
    assert summary["D"].tolist() == [7.0, 14.0]


def test_attractor_requires_seven_consecutive_qualifying_days():
    rows = [
        (f"2026-08-{day:02d}", "01:30", "08:30")
        for day in range(1, 8)
    ]
    summary = summarize(rows)
    assert summary.iloc[:6]["in_attractor"].tolist() == [0, 0, 0, 0, 0, 0]
    assert summary.iloc[6]["in_attractor"] == 1


def test_missing_day_breaks_attractor_streak():
    rows = [
        (f"2026-08-{day:02d}", "01:30", "08:30")
        for day in [1, 2, 3, 4, 5, 6, 8]
    ]
    assert summarize(rows).iloc[-1]["in_attractor"] == 0


def test_runtime_thresholds_reclassify_full_history():
    rows = [
        (f"2026-08-{day:02d}", "02:00", "09:00")
        for day in range(1, 8)
    ]
    assert summarize(rows, p_limit=1.0).iloc[-1]["in_attractor"] == 1
    assert summarize(rows, p_limit=0.4).iloc[-1]["in_attractor"] == 0


@pytest.mark.parametrize("phase, expected", [(None, False), (float("nan"), False), (6.1, False), (-6.1, False), (6.0, True), (0.0, True)])
def test_light_guidance_safe_mode(phase, expected):
    assert can_recommend_light(phase) is expected


def test_biological_utc_offset_uses_sustained_phase_displacement():
    assert estimate_biological_utc_offset([3.0] * 7, 8.0) == pytest.approx(5.0)
    assert estimate_biological_utc_offset([-2.0] * 7, 8.0) == pytest.approx(10.0)


def test_biological_utc_offset_uses_latest_seven_valid_values():
    result = estimate_biological_utc_offset([None, 8.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0], 8.0)
    assert result == pytest.approx(6.0)


def test_biological_utc_offset_handles_phase_seam():
    assert estimate_biological_utc_offset([11.5, -11.5], 8.0) == pytest.approx(-4.0)
    assert estimate_biological_utc_offset([], 8.0) is None


def test_live_state_estimates_missed_sleep_without_mutating_formal_debt():
    live_state = calculate_live_state(
        datetime(2026, 8, 7, 8, 30),
        datetime(2026, 8, 8, 4, 40),
        "08:30",
        7.0,
        2.0,
    )
    assert live_state["assumed_awake_hours"] == pytest.approx(20 + 10 / 60)
    assert live_state["missed_sleep_hours"] == pytest.approx(3 + 10 / 60)
    assert live_state["projected_debt"] == pytest.approx(5 + 10 / 60)


def test_live_state_is_zero_before_target_sleep_window_and_caps_at_sleep_need():
    before_sleep = calculate_live_state(
        datetime(2026, 8, 7, 8, 30), datetime(2026, 8, 7, 23, 0), "08:30", 7.0, 2.0
    )
    after_target_wake = calculate_live_state(
        datetime(2026, 8, 7, 8, 30), datetime(2026, 8, 8, 12, 0), "08:30", 7.0, 2.0
    )
    assert before_sleep["missed_sleep_hours"] == 0.0
    assert after_target_wake["missed_sleep_hours"] == 7.0
    assert after_target_wake["projected_debt"] == 9.0
    assert calculate_live_state(None, datetime(2026, 8, 8), "08:30", 7.0, 2.0) is None
