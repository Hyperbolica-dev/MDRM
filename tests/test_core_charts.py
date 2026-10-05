import pandas as pd

from ui.core_charts import build_core_trend_figure, filter_points_by_range


LABELS = {
    "chart_wake": "Wake",
    "chart_sleep_debt": "Debt",
    "chart_habit": "Habit",
    "chart_date": "Date",
    "chart_title": "Core ({range})",
}


def test_core_trend_charts_connect_missing_values():
    frame = pd.DataFrame([
        {"rhythm_day": "2026-09-01", "wake_time": "08:00", "D": 1.0, "H": 0.8},
        {"rhythm_day": "2026-09-02", "wake_time": "N/A", "D": None, "H": None},
        {"rhythm_day": "2026-09-03", "wake_time": "08:15", "D": 0.5, "H": 0.9},
    ])

    figure = build_core_trend_figure(frame, "All", LABELS)

    assert figure is not None
    assert len(figure.data) == 3
    assert all(trace.connectgaps is True for trace in figure.data)


def test_core_trend_charts_include_routine_stability_trace_when_available():
    frame = pd.DataFrame([
        {"rhythm_day": "2026-09-01", "wake_time": "08:00", "D": 1.0, "H": 0.8, "routine_stability": 0.6},
        {"rhythm_day": "2026-09-02", "wake_time": "08:15", "D": 0.8, "H": 0.82, "routine_stability": 0.9},
    ])
    labels = {**LABELS, "chart_routine_stability": "Routine"}

    figure = build_core_trend_figure(frame, "All", labels)

    assert figure is not None
    assert len(figure.data) == 4
    assert figure.data[-1].name == "Routine"
    assert figure.data[-1].connectgaps is True


def test_core_trend_range_filter_keeps_latest_window_sorted():
    frame = pd.DataFrame([
        {"rhythm_day": "2026-08-01", "wake_time": "08:00", "D": 1.0, "H": 0.8},
        {"rhythm_day": "2026-09-01", "wake_time": "08:00", "D": 0.5, "H": 0.9},
    ])

    selected = filter_points_by_range(frame, "30D")

    assert selected["rhythm_day"].dt.strftime("%Y-%m-%d").tolist() == ["2026-09-01"]
