import numpy as np
import pandas as pd
import plotly.graph_objects as go


def prepare_phase_space_3d_frame(daily_points: pd.DataFrame) -> pd.DataFrame:
    if daily_points.empty:
        return pd.DataFrame()
    ordered = daily_points.copy().sort_values("rhythm_day")
    ordered["rhythm_day"] = pd.to_datetime(ordered["rhythm_day"], errors="coerce")
    ordered["P"] = pd.to_numeric(ordered["P"], errors="coerce")
    ordered["D"] = pd.to_numeric(ordered["D"], errors="coerce")
    ordered = ordered.dropna(subset=["rhythm_day"])
    if ordered.empty:
        return pd.DataFrame()
    latest_day = ordered["rhythm_day"].max()
    plot_frame = ordered.dropna(subset=["P", "D"]).copy()
    if plot_frame.empty:
        return pd.DataFrame()
    plot_frame["time_offset_days"] = (
        plot_frame["rhythm_day"] - latest_day
    ).dt.total_seconds() / 86400.0
    age_days = -plot_frame["time_offset_days"]
    if age_days.max() == age_days.min():
        plot_frame["time_bucket"] = 3
    else:
        plot_frame["time_bucket"] = pd.cut(
            age_days,
            bins=np.linspace(float(age_days.min()), float(age_days.max()), 5),
            labels=False,
            include_lowest=True,
        ).fillna(0).astype(int)
    return plot_frame


def build_phase_space_3d_figure(daily_points: pd.DataFrame) -> go.Figure | None:
    plot_frame = prepare_phase_space_3d_frame(daily_points)
    if plot_frame.empty:
        return None
    fig = go.Figure()
    bucket_colors = ["#9ca3af", "#6b7280", "#3b82f6", "#1d4ed8"]
    bucket_opacities = [0.25, 0.42, 0.62, 0.86]
    bucket_sizes = [3.5, 4.5, 5.5, 7.0]
    for bucket in range(4):
        bucket_frame = plot_frame[plot_frame["time_bucket"] == bucket]
        if bucket_frame.empty:
            continue
        fig.add_trace(go.Scatter3d(
            x=bucket_frame["P"],
            y=bucket_frame["D"],
            z=bucket_frame["time_offset_days"],
            mode="lines+markers",
            line=dict(color=bucket_colors[bucket], width=2.0),
            marker=dict(color=bucket_colors[bucket], size=bucket_sizes[bucket], opacity=bucket_opacities[bucket]),
            opacity=bucket_opacities[bucket],
            name=f"Age bucket {bucket + 1}",
            showlegend=False,
            hovertemplate="P=%{x:.2f} h<br>D=%{y:.2f} h<br>Time=%{z:.0f} d<extra></extra>",
        ))
    disturbance = plot_frame[plot_frame["disturbance"].fillna(0).astype(bool)] if "disturbance" in plot_frame else pd.DataFrame()
    if not disturbance.empty:
        fig.add_trace(go.Scatter3d(
            x=disturbance["P"],
            y=disturbance["D"],
            z=disturbance["time_offset_days"],
            mode="markers",
            marker=dict(symbol="diamond", color="#e76f51", size=8, line=dict(color="#7f1d1d", width=1)),
            name="Disturbance",
            hovertemplate="P=%{x:.2f} h<br>D=%{y:.2f} h<br>Time=%{z:.0f} d<br>Disturbance<extra></extra>",
        ))
    latest = plot_frame.iloc[-1]
    latest_name = "Current" if latest["time_offset_days"] == 0 else "Latest plottable"
    fig.add_trace(go.Scatter3d(
        x=[latest["P"]],
        y=[latest["D"]],
        z=[latest["time_offset_days"]],
        mode="markers",
        marker=dict(color="#ffb703", size=11, line=dict(color="#1f2937", width=1.5)),
        name=latest_name,
        hovertemplate="P=%{x:.2f} h<br>D=%{y:.2f} h<br>Time=%{z:.0f} d<extra></extra>",
    ))
    fig.update_layout(
        title="P-D-Time Trajectory [Experimental]",
        height=620,
        margin=dict(l=0, r=0, t=55, b=0),
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.08, xanchor="left", x=0),
        scene=dict(
            camera=dict(eye=dict(x=0.0, y=0.0, z=2.5)),
            xaxis=dict(title="P phase (h)"),
            yaxis=dict(title="D sleep debt (h)"),
            zaxis=dict(title="Time from latest (days)"),
            aspectmode="auto",
        ),
    )
    return fig
