from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def filter_points_by_range(daily_points: pd.DataFrame, range_label: str):
    if daily_points.empty:
        return daily_points
    filtered = daily_points.copy()
    filtered["rhythm_day"] = pd.to_datetime(filtered["rhythm_day"], errors="coerce")
    latest_date = filtered["rhythm_day"].dt.date.max()
    if pd.isna(latest_date):
        return filtered

    if range_label == "All":
        return filtered.sort_values("rhythm_day")

    range_map = {"7D": 7, "30D": 30, "90D": 90}
    days = range_map.get(range_label)
    if days is None:
        return filtered.sort_values("rhythm_day")
    start_date = latest_date - timedelta(days=days - 1)
    return filtered[
        (filtered["rhythm_day"].dt.date >= start_date)
        & (filtered["rhythm_day"].dt.date <= latest_date)
    ].sort_values("rhythm_day")


def build_core_trend_figure(daily_points: pd.DataFrame, range_label: str, labels: dict):
    filtered = filter_points_by_range(daily_points, range_label)
    if filtered.empty:
        return None

    chart_frame = filtered.copy()
    chart_frame["rhythm_day"] = pd.to_datetime(chart_frame["rhythm_day"], errors="coerce")
    chart_frame = chart_frame.dropna(subset=["rhythm_day"])
    if chart_frame.empty:
        return None

    def clock_to_decimal(value):
        if not isinstance(value, str) or not value:
            return pd.NA
        parsed = pd.to_datetime(value, format="%H:%M", errors="coerce")
        if pd.isna(parsed):
            return pd.NA
        return parsed.hour + parsed.minute / 60.0

    chart_frame["wake_clock_hour"] = chart_frame["wake_time"].apply(clock_to_decimal)
    chart_frame = chart_frame.sort_values("rhythm_day")

    has_routine_stability = "routine_stability" in chart_frame.columns
    chart_rows = 4 if has_routine_stability else 3
    fig = make_subplots(rows=chart_rows, cols=1, shared_xaxes=True, vertical_spacing=0.08)

    fig.add_trace(go.Scatter(
        x=chart_frame["rhythm_day"], y=chart_frame["wake_clock_hour"],
        mode="lines+markers", marker=dict(color="#1d3557", size=6),
        line=dict(color="#1d3557", width=2),
        connectgaps=True,
        name=labels["chart_wake"],
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            f"{labels['chart_wake']}: %{{y:.1f}}<br>"
            "HH:MM: %{customdata}<extra></extra>"
        ),
        customdata=chart_frame["wake_time"],
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=chart_frame["rhythm_day"], y=chart_frame["D"],
        mode="lines+markers", marker=dict(color="#457b9d", size=6),
        line=dict(color="#457b9d", width=2),
        connectgaps=True,
        name=labels["chart_sleep_debt"],
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            f"{labels['chart_sleep_debt']}: %{{y:.2f}} h<extra></extra>"
        ),
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=chart_frame["rhythm_day"], y=chart_frame["H"],
        mode="lines+markers", marker=dict(color="#2a9d8f", size=6),
        line=dict(color="#2a9d8f", width=2),
        connectgaps=True,
        name=labels["chart_habit"],
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            f"{labels['chart_habit']}: %{{y:.3f}}<extra></extra>"
        ),
    ), row=3, col=1)

    if has_routine_stability:
        fig.add_trace(go.Scatter(
            x=chart_frame["rhythm_day"], y=chart_frame["routine_stability"],
            mode="lines+markers", marker=dict(color="#f4a261", size=6),
            line=dict(color="#f4a261", width=2),
            connectgaps=True,
            name=labels["chart_routine_stability"],
            hovertemplate=(
                "<b>%{x|%Y-%m-%d}</b><br>"
                f"{labels['chart_routine_stability']}: %{{y:.0%}}<extra></extra>"
            ),
        ), row=4, col=1)

    fig.update_yaxes(title_text=labels["chart_wake"], row=1, col=1)
    fig.update_yaxes(title_text=labels["chart_sleep_debt"], row=2, col=1)
    fig.update_yaxes(title_text=labels["chart_habit"], row=3, col=1)
    if has_routine_stability:
        fig.update_yaxes(title_text=labels["chart_routine_stability"], range=[0, 1], row=4, col=1)
        fig.update_xaxes(title_text=labels["chart_date"], row=4, col=1)
    else:
        fig.update_xaxes(title_text=labels["chart_date"], row=3, col=1)
    fig.update_layout(
        title=labels["chart_title"].format(range=range_label),
        showlegend=False,
        height=720 if has_routine_stability else 600,
        margin=dict(l=50, r=20, t=50, b=50),
    )
    return fig
