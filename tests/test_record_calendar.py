from datetime import date

import pandas as pd

from ui.record_calendar import build_date_input_calendar_css, classify_entry_dates, classify_recorded_days


def test_recorded_days_are_classified_by_phase_without_legacy_debt():
    summary = pd.DataFrame([
        {"rhythm_day": "2026-09-14", "P": 0.2, "in_attractor": True},
        {"rhythm_day": "2026-09-15", "P": 1.4, "in_attractor": False},
        {"rhythm_day": "2026-09-16", "P": -1.3, "in_attractor": False},
        {"rhythm_day": "2026-09-17", "P": 0.4, "in_attractor": False},
        {"rhythm_day": "2026-09-18", "P": None, "in_attractor": False},
    ])
    recorded = pd.date_range("2026-09-14", "2026-09-18")

    statuses = classify_recorded_days(summary, recorded)

    assert statuses == {
        date(2026, 9, 14): "phase_aligned_debt",
        date(2026, 9, 15): "phase_delayed",
        date(2026, 9, 16): "phase_advanced",
        date(2026, 9, 17): "phase_aligned_debt",
        date(2026, 9, 18): "phase_undefined",
    }


def test_inferred_summary_day_without_record_is_not_colored():
    summary = pd.DataFrame([{"rhythm_day": "2026-09-19", "P": 2.0, "in_attractor": False}])

    assert classify_recorded_days(summary, []) == {}


def test_entry_calendar_marks_selected_date_when_rhythm_day_moves_forward():
    summary = pd.DataFrame([{"rhythm_day": "2026-09-19", "P": 2.0, "in_attractor": False}])
    records = pd.DataFrame([{"date": "2026-09-18"}])
    sessions = pd.DataFrame([{"date": "2026-09-18", "main_sleep_day": "2026-09-19"}])

    assert classify_entry_dates(summary, records, sessions) == {
        date(2026, 9, 18): "phase_delayed"
    }


def test_saved_date_is_marked_even_without_derived_state():
    records = pd.DataFrame([{"date": "2026-09-18"}])

    assert classify_entry_dates(pd.DataFrame(), records, pd.DataFrame()) == {
        date(2026, 9, 18): "phase_undefined"
    }


def test_date_input_css_uses_pale_status_colors_and_accessible_date_labels():
    css = build_date_input_calendar_css({date(2026, 9, 18): "in_attractor"})

    assert 'role="gridcell"' in css
    assert "September 18th 2026" in css
    assert "2026年9月18日" in css
    assert "rgba(42,157,91,0.18)" in css
    assert "border-radius:50%" in css


def test_calendar_green_requires_seven_recorded_consecutive_phase_days():
    dates = pd.date_range("2026-09-01", periods=7)
    summary = pd.DataFrame({"rhythm_day": dates, "P": 0.2, "D": 99, "in_attractor": False})
    assert classify_recorded_days(summary, dates)[dates[-1].date()] == "in_attractor"
    assert classify_recorded_days(summary, dates.delete(3))[dates[-1].date()] == "phase_aligned_debt"


def test_unknown_duration_breaks_green_streak_without_poisoning_later_known_days():
    dates = pd.date_range("2026-09-01", periods=15)
    summary = pd.DataFrame({"rhythm_day": dates, "P": 0.2, "sleep_duration_known": True, "state_estimated": True})
    summary.loc[6, "sleep_duration_known"] = False
    statuses = classify_recorded_days(summary, dates)
    assert statuses[dates[6].date()] == "phase_undefined"
    assert statuses[dates[7].date()] == "phase_aligned_debt"
    assert statuses[dates[13].date()] == "in_attractor"


def test_mixed_entry_date_is_order_independent_and_unknown_takes_precedence():
    summary = pd.DataFrame({"rhythm_day": ["2026-09-18", "2026-09-19"], "P": [-2, 2], "sleep_duration_known": True})
    records = pd.DataFrame({"date": ["2026-09-18", "2026-09-18"]})
    sessions = pd.DataFrame({"date": ["2026-09-18", "2026-09-18"], "main_sleep_day": ["2026-09-18", "2026-09-19"]})
    expected = {date(2026, 9, 18): "phase_mixed"}
    assert classify_entry_dates(summary, records, sessions) == expected
    assert classify_entry_dates(summary, records, sessions.iloc[::-1]) == expected
    summary.loc[0, "sleep_duration_known"] = False
    assert classify_entry_dates(summary, records, sessions) == {date(2026, 9, 18): "phase_undefined"}
