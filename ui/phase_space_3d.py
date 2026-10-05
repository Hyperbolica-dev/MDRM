import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ui.phase_space import build_phase_line_frame


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
        ).fillna(0).astype(int).rsub(3)
    return plot_frame


def build_phase_space_3d_figure(daily_points: pd.DataFrame, view="oblique", chinese=False, p_limit=1.0, d_limit=5.0) -> go.Figure | None:
    plot_frame = prepare_phase_space_3d_frame(daily_points)
    if plot_frame.empty:
        return None
    fig = go.Figure()
    line_frame = build_phase_line_frame(plot_frame)
    fig.add_trace(go.Scatter3d(
        x=line_frame["P"], y=line_frame["D"], z=line_frame["time_offset_days"],
        mode="lines", line=dict(color="#64748b", width=3),
        showlegend=False, hoverinfo="skip", connectgaps=False,
    ))
    hover = "<b>%{customdata[0]}</b><br>P=%{x:.2f} h<br>D=%{y:.2f} h<br>" + ("距最新记录" if chinese else "Days from latest record") + "=%{z:.0f}<br>%{customdata[1]}<extra></extra>"
    plot_frame["date_label"] = plot_frame["rhythm_day"].dt.strftime("%Y-%m-%d")
    estimated = plot_frame.get("state_estimated", pd.Series(False, index=plot_frame.index)).fillna(False).astype(bool)
    plot_frame["state_label"] = estimated.map({True: "未知时长历史：估计状态" if chinese else "Unknown duration in history: estimated state", False: "由记录计算的模型状态" if chinese else "Model state from records"})
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
            mode="markers",
            line=dict(color=bucket_colors[bucket], width=2.0),
            marker=dict(color=bucket_colors[bucket], size=bucket_sizes[bucket], opacity=bucket_opacities[bucket]),
            name=f"Age bucket {bucket + 1}",
            showlegend=False,
            customdata=bucket_frame[["date_label", "state_label"]].to_numpy(),
            hovertemplate=hover,
        ))
    disturbance = plot_frame[plot_frame["disturbance"].fillna(0).astype(bool)] if "disturbance" in plot_frame else pd.DataFrame()
    if not disturbance.empty:
        fig.add_trace(go.Scatter3d(
            x=disturbance["P"],
            y=disturbance["D"],
            z=disturbance["time_offset_days"],
            mode="markers",
            marker=dict(symbol="diamond", color="#e76f51", size=8, line=dict(color="#7f1d1d", width=1)),
            name="扰动" if chinese else "Disturbance",
            customdata=disturbance[["date_label", "state_label"]].to_numpy(),
            hovertemplate=hover,
        ))
    latest = plot_frame.iloc[-1]
    latest_name = ("最新记录" if chinese else "Latest recorded") if latest["time_offset_days"] == 0 else ("最近可绘制" if chinese else "Latest plottable")
    fig.add_trace(go.Scatter3d(
        x=[latest["P"]],
        y=[latest["D"]],
        z=[latest["time_offset_days"]],
        mode="markers+text",
        text=[latest["date_label"]],
        textposition="top center",
        marker=dict(color="#ffb703", size=11, line=dict(color="#1f2937", width=1.5)),
        name=latest_name,
        customdata=latest[["date_label", "state_label"]].to_numpy().reshape(1, -1),
        hovertemplate=hover,
    ))
    fig.add_trace(go.Scatter3d(
        x=[-p_limit, p_limit, p_limit, -p_limit, -p_limit],
        y=[0, 0, d_limit, d_limit, 0], z=[0] * 5,
        mode="lines", line=dict(color="#2a9d8f", width=4, dash="dash"),
        name="最新日期目标区边界" if chinese else "Target boundary at latest date", hoverinfo="skip",
    ))
    cameras = {
        "oblique": dict(eye=dict(x=1.6, y=1.5, z=1.2), up=dict(x=0, y=0, z=1)),
        "pd": dict(eye=dict(x=0, y=0, z=2.5), up=dict(x=0, y=1, z=0)),
        "phase_time": dict(eye=dict(x=0, y=2.5, z=0), up=dict(x=0, y=0, z=1)),
        "debt_time": dict(eye=dict(x=2.5, y=0, z=0), up=dict(x=0, y=0, z=1)),
    }
    camera = {**cameras.get(view, cameras["oblique"]), "projection": {"type": "orthographic"}}
    fig.update_layout(
        title="P–D–时间轨迹" if chinese else "P–D–Time trajectory",
        height=620,
        margin=dict(l=0, r=0, t=55, b=70),
        uirevision=f"phase-time:{view}",
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.08, xanchor="left", x=0),
        scene=dict(
            camera=camera,
            xaxis=dict(title="P 目标偏移 (h)" if chinese else "P phase (h)"),
            yaxis=dict(title="D 模型睡眠债 (h)" if chinese else "D sleep debt (h)"),
            zaxis=dict(title="距最新记录 (天)" if chinese else "Time from latest (days)"),
            aspectmode="manual", aspectratio=dict(x=1, y=1, z=1.3),
        ),
    )
    return fig
