import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
from plotly.colors import sample_colorscale
import plotly.graph_objects as go
import streamlit as st

from model.phase_observation import build_state_occupancy, summarize_phase_observations, prepare_phase_observations


def prepare_pressure_plot_points(points):
    frame = prepare_phase_observations(points)
    frame.loc[~frame["phase_usable"], "P"] = np.nan
    frame.loc[~frame["pressure_usable"], ["S", "S_low", "S_high"]] = np.nan
    return frame


def pressure_hover_data(frame):
    times = pd.to_datetime(frame.get("pressure_at", pd.Series(index=frame.index, dtype="datetime64[ns]")), errors="coerce").dt.strftime("%Y-%m-%d %H:%M").fillna("—")
    return list(zip(pd.to_datetime(frame["rhythm_day"]).dt.strftime("%Y-%m-%d"), frame["P"], frame["S_low"], frame["S_high"], times))


def pressure_hover_template(chinese):
    return "%{customdata[0]}<br>P=%{customdata[1]:.2f} h<br>S=%{customdata[2]:.1f}–%{customdata[3]:.1f}<br>" + ("压力时点：" if chinese else "Pressure at: ") + "%{customdata[4]}<extra></extra>"


def build_pressure_figure(points, chinese=False, view=None):
    ordered = prepare_pressure_plot_points(points).sort_values("rhythm_day")
    valid = ordered.dropna(subset=["P", "S"])
    if valid.empty:
        return None
    days = pd.to_datetime(valid["rhythm_day"])
    latest_day = pd.to_datetime(ordered["rhythm_day"]).max()
    x, y, z = [], [], []
    previous = None
    for row in valid.to_dict("records"):
        day = pd.Timestamp(row["rhythm_day"])
        if previous is not None and ((day - previous[0]).days != 1 or abs(row["P"] - previous[1]) > 12):
            x.append(None)
            y.append(None)
            z.append(None)
        x.append(row["P"])
        y.append(row["S"])
        z.append((day - latest_day).days)
        previous = day, row["P"]
    figure = go.Figure()
    trace_type = go.Scatter3d if view else go.Scatter
    time_values = (days - latest_day).dt.days
    line_args = {"z": z} if view else {}
    marker_args = {"z": time_values} if view else {}
    figure.add_trace(trace_type(x=x, y=y, mode="lines", line=dict(color="#64748b", width=2), connectgaps=False, showlegend=False, hoverinfo="skip", **line_args))
    figure.add_trace(trace_type(
        x=valid["P"], y=valid["S"], mode="markers",
        marker=dict(size=6 if view else 9, color=time_values, colorscale=[[0, "#9ca3af"], [1, "#2563eb"]]),
        error_y=dict(type="data", symmetric=False, array=valid["S_high"] - valid["S"], arrayminus=valid["S"] - valid["S_low"]),
        customdata=pressure_hover_data(valid),
        hovertemplate=pressure_hover_template(chinese),
        showlegend=False, **marker_args,
    ))
    latest = valid.iloc[-1]
    latest_args = {"z": [(pd.Timestamp(latest["rhythm_day"]) - latest_day).days]} if view else {}
    figure.add_trace(trace_type(x=[latest["P"]], y=[latest["S"]], mode="markers", marker=dict(size=10 if view else 14, color="#ffb703"), customdata=pressure_hover_data(valid.tail(1)), hovertemplate=pressure_hover_template(chinese), name="最近可绘制记录" if chinese else "Latest plottable record", **latest_args))
    pressure_label = "S 醒后稳态压力模拟（0–100）" if chinese else "S post-sleep pressure model (0–100)"
    phase_label = "P 目标偏移（小时）" if chinese else "P target offset (hours)"
    figure.update_layout(height=520, margin=dict(l=45, r=15, t=35, b=45), legend=dict(orientation="h", y=-0.12))
    if view:
        eyes = {"oblique": (1.6, 1.5, 1.2), "phase_pressure": (0, 0, 2.5), "phase_time": (0, 2.5, 0), "pressure_time": (2.5, 0, 0)}
        eye = eyes[view]
        figure.update_layout(scene=dict(xaxis_title=phase_label, yaxis=dict(title=pressure_label, range=[0, 100]), zaxis_title="距最新记录（天）" if chinese else "Days from latest record", camera=dict(eye=dict(zip(["x", "y", "z"], eye)), up=dict(x=0, y=1 if view == "phase_pressure" else 0, z=0 if view == "phase_pressure" else 1), projection=dict(type="orthographic")), aspectmode="manual", aspectratio=dict(x=1, y=1, z=1.3)), uirevision=f"pressure:{view}")
    else:
        figure.update_xaxes(title_text=phase_label, zeroline=True)
        figure.update_yaxes(title_text=pressure_label, range=[0, 100])
    return figure


def build_state_counts(points):
    valid = points.dropna(subset=["P", "S"])
    phase = (valid["P"].to_numpy() + 12) % 24 - 12
    counts, _, _ = np.histogram2d(phase, valid["S"], bins=[np.arange(-12, 13, 1), np.arange(0, 101, 10)])
    return counts.T


def build_recent_figure(points, chinese=False, polar=False):
    ordered = prepare_pressure_plot_points(points).sort_values("rhythm_day")
    cutoff = pd.to_datetime(ordered["rhythm_day"]).max() - pd.Timedelta(days=6)
    valid = ordered[pd.to_datetime(ordered["rhythm_day"]) >= cutoff].dropna(subset=["P", "S"])
    if valid.empty:
        return None
    figure = go.Figure()
    rows = valid.to_dict("records")
    if not polar:
        for previous, current in zip(rows, rows[1:]):
            gap = (pd.Timestamp(current["rhythm_day"]) - pd.Timestamp(previous["rhythm_day"])).days
            if gap == 1 and abs(current["P"] - previous["P"]) <= 12:
                age = (pd.Timestamp(current["rhythm_day"]) - cutoff).days / 6
                figure.add_trace(go.Scatter(x=[previous["P"], current["P"]], y=[previous["S"], current["S"]], mode="lines", line=dict(color=sample_colorscale("Blues", [0.25 + 0.75 * age])[0], width=3), hoverinfo="skip", showlegend=False))
    days = pd.to_datetime(valid["rhythm_day"])
    positions = ["top center", "bottom center", "middle right", "middle left"]
    symbols = ["circle"] * (len(valid) - 1) + ["diamond"]
    shared = dict(mode="markers+text", text=days.dt.strftime("%m-%d"), textposition=[positions[index % 4] for index in range(len(valid))], marker=dict(size=10, symbol=symbols, color=(days-cutoff).dt.days, cmin=0, cmax=6, colorscale=[[0,"#94a3b8"],[1,"#1d4ed8"]], line=dict(width=1, color="#334155")), customdata=pressure_hover_data(valid), hovertemplate=pressure_hover_template(chinese), showlegend=False)
    if polar:
        figure.add_trace(go.Scatterpolar(theta=valid["P"] * 15, r=25 + valid["S"], **shared))
        for row in rows:
            figure.add_trace(go.Scatterpolar(theta=[row["P"]*15]*2, r=[25+row["S_low"], 25+row["S_high"]], mode="lines", line=dict(color="#64748b", width=2), hoverinfo="skip", showlegend=False))
        figure.update_layout(polar=dict(angularaxis=dict(rotation=90, direction="clockwise", tickvals=[0,45,90,135,180,225,270,315], ticktext=["目标 0" if chinese else "Target 0", "+3h", "+6h", "+9h", "±12h", "−9h", "−6h", "−3h"]), radialaxis=dict(range=[0,125], tickvals=[25,50,75,100,125], ticktext=["S=0","25","50","75","100"])))
    else:
        figure.add_trace(go.Scatter(x=valid["P"], y=valid["S"], error_y=dict(type="data", symmetric=False, array=valid["S_high"]-valid["S"], arrayminus=valid["S"]-valid["S_low"]), **shared))
        figure.add_vline(x=0, line_dash="dot", line_color="#64748b")
        figure.update_xaxes(title_text="P：提前 ← 目标偏移（h） → 延后" if chinese else "P: earlier ← target offset (h) → later", range=[-12,12])
        figure.update_yaxes(title_text="S：醒后压力模拟" if chinese else "S: post-sleep pressure model", range=[0,100])
    figure.update_layout(height=480, margin=dict(l=45,r=30,t=35,b=45))
    return figure


def build_pressure_timeline(points, chinese=False):
    ordered = prepare_pressure_plot_points(points).sort_values("rhythm_day")
    ordered["rhythm_day"] = pd.to_datetime(ordered["rhythm_day"])
    ordered = ordered.set_index("rhythm_day").reindex(pd.date_range(ordered["rhythm_day"].min(), ordered["rhythm_day"].max()))
    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12)
    figure.add_trace(go.Scatter(x=ordered.index, y=ordered["P"], mode="markers", name="P", marker=dict(color="#2563eb")), row=1, col=1)
    hover_frame = ordered.rename_axis("rhythm_day").reset_index()
    figure.add_trace(go.Scatter(x=ordered.index, y=ordered["S"], mode="markers", name="S", error_y=dict(type="data", symmetric=False, array=ordered["S_high"]-ordered["S"], arrayminus=ordered["S"]-ordered["S_low"]), marker=dict(color="#0f766e"), customdata=pressure_hover_data(hover_frame), hovertemplate=pressure_hover_template(chinese)), row=2, col=1)
    figure.update_yaxes(title_text="P (h)", range=[-12,12], row=1,col=1)
    figure.update_yaxes(title_text="S (0–100)", range=[0,100], row=2,col=1)
    figure.update_layout(height=400, showlegend=False, margin=dict(l=45,r=20,t=15,b=35))
    return figure


def build_occupancy_figure(occupancy, chinese=False, polar=False):
    definite, possible = occupancy["definite"], occupancy["possible"]
    figure = go.Figure()
    if polar:
        pressure_bins, phase_bins = np.nonzero(possible)
        counts = definite[pressure_bins, phase_bins]
        figure.add_trace(go.Scatterpolar(
            theta=(phase_bins - 11.5) * 15, r=25 + pressure_bins * 10 + 5, mode="markers",
            marker=dict(size=6 + 4 * np.sqrt(counts), symbol=["circle" if count else "circle-open" for count in counts], color=counts, colorscale="Blues", cmin=0, cmax=max(1, int(definite.max())), line=dict(width=1, color="#64748b")),
            customdata=list(zip(phase_bins - 11.5, pressure_bins * 10 + 5, counts, possible[pressure_bins, phase_bins])),
            hovertemplate="P: %{customdata[0]} ±0.5 h<br>S: %{customdata[1]} ±5<br>" + ("确定落入 %{customdata[2]} 日；可能覆盖 %{customdata[3]} 日" if chinese else "Fully inside: %{customdata[2]} days; possibly inside: %{customdata[3]} days") + "<extra></extra>",
            showlegend=False,
        ))
        figure.update_layout(polar=dict(angularaxis=dict(rotation=90, direction="clockwise", tickvals=[0,45,90,135,180,225,270,315], ticktext=["目标 0" if chinese else "Target 0", "+3h", "+6h", "+9h", "±12h", "−9h", "−6h", "−3h"]), radialaxis=dict(range=[0,125], tickvals=[25,50,75,100,125], ticktext=["S=0","25","50","75","100"])))
    else:
        figure.add_trace(go.Heatmap(
            x=np.arange(-11.5,12,1), y=np.arange(5,100,10), z=np.where(possible>0,definite,np.nan),
            customdata=np.stack([definite, possible], axis=-1), colorscale=[[0,"#f8fafc"],[1,"#1d4ed8"]], zmin=0, zmax=max(1,int(definite.max())), colorbar=dict(title="确定日数" if chinese else "Fully inside", tickformat="d"),
            hovertemplate="P: %{x} ±0.5 h<br>S: %{y} ±5<br>" + ("确定落入 %{customdata[0]} 日；可能覆盖 %{customdata[1]} 日" if chinese else "Fully inside: %{customdata[0]} days; possibly inside: %{customdata[1]} days") + "<extra></extra>",
        ))
        pressure_bins, phase_bins = np.nonzero((possible>0) & (definite==0))
        figure.add_trace(go.Scatter(x=phase_bins-11.5, y=pressure_bins*10+5, mode="markers", marker=dict(size=8, symbol="circle-open", color="#64748b"), hoverinfo="skip", name="仅可能覆盖" if chinese else "Possible only"))
        figure.update_xaxes(title_text="P：提前 ← 目标偏移（h） → 延后" if chinese else "P: earlier ← target offset (h) → later", range=[-12,12])
        figure.update_yaxes(title_text="S (0–100)",range=[0,100])
    figure.update_layout(height=460, margin=dict(l=45,r=35,t=25,b=45))
    return figure


def render_phase_summary(points, chinese):
    summary = summarize_phase_observations(points)
    coverage, distance = st.columns(2)
    coverage.metric("可用相位 / 压力日数" if chinese else "Usable phase / pressure days", f"{summary['phase_days']} / {summary['pressure_days']}")
    median = summary["median_target_distance"]
    distance.metric("离目标的距离中位数" if chinese else "Median distance from target", "—" if median is None else f"{median:.2f} h")
    st.caption("目标距离为 |P| 的中位数，至少需 3 个可用日；提前和延后都可能离目标更远。睡眠量未知时不将 P 当作可用相位。" if chinese else "Target distance is median |P|, requiring at least 3 usable days. Either earlier or later may be farther from target. Unknown sleep duration excludes P from this summary.")
    delta = summary["phase_change"]
    if delta is not None:
        start, end = summary["previous_day"], summary["latest_day"]
        direction = ("延后" if delta > 0 else "提前") if chinese else ("later" if delta > 0 else "earlier")
        target_delta = summary["target_distance_change"]
        target_word = ("更远" if target_delta > 0 else "更近") if chinese else ("farther from" if target_delta > 0 else "closer to")
        movement = ("基本不变" if chinese else "essentially unchanged") if abs(delta)<0.005 else (f"{direction} {abs(delta):.2f} h" if chinese else f"{abs(delta):.2f} h {direction}")
        target = ("与目标的距离基本不变" if chinese else "distance to target essentially unchanged") if abs(target_delta)<0.005 else (f"离目标{target_word} {abs(target_delta):.2f} h" if chinese else f"{abs(target_delta):.2f} h {target_word} target")
        st.write(f"{start:%m-%d} → {end:%m-%d}：{movement}；{target}。" if chinese else f"{start:%m-%d} → {end:%m-%d}: {movement}; {target}.")
    else:
        st.caption("最新两日缺少可比较相位或方向不唯一，不推断相邻日早晚变化。" if chinese else "Latest two days lack comparable phase or a unique circular direction; no adjacent-day phase change is inferred.")
    lower, upper = summary["pressure_change_low"], summary["pressure_change_high"]
    if lower is not None:
        direction = ("上升" if lower > 0 else "下降" if upper < 0 else "范围重叠，无法确定升降") if chinese else ("higher" if lower > 0 else "lower" if upper < 0 else "overlapping ranges; direction unresolved")
        st.caption(f"最新连续两日醒后 S：{direction}，变化情景范围 {lower:+.1f} 至 {upper:+.1f} 单位。比较的是各日记录结束时点，午睡和时点不同也会影响结果。" if chinese else f"Post-sleep S on the latest consecutive days: {direction}; change range {lower:+.1f} to {upper:+.1f} units. End-of-record times and naps may differ between days.")


def render_pressure_trajectory(points, chinese):
    st.subheader("相位与睡眠压力" if chinese else "Phase and sleep pressure")
    if points.empty:
        st.info("记录后显示；不把空白日期当作通宵。" if chinese else "Record sleep to see the trajectory; missing days are not all-nighters.")
        return
    range_days = st.radio("轨迹时间范围" if chinese else "Pressure trajectory range", [7,30,90], horizontal=True, index=1)
    days = pd.to_datetime(points["rhythm_day"])
    selected = points[days >= days.max()-pd.Timedelta(days=range_days-1)]
    st.caption(f"截至 {days.max():%Y-%m-%d} 的 {range_days} 个日历日；空白不等于通宵。" if chinese else f"{range_days} calendar days ending {days.max():%Y-%m-%d}; missing is not an all-nighter.")
    render_phase_summary(selected, chinese)
    st.caption("P 是睡眠时间代理，不是生物钟实测。S 是记录结束时的固定参数压力模拟；点是情景中点，竖线是范围，不是置信区间。范围不包含个人参数差异，变窄不代表个体校准完成。" if chinese else "P is a sleep-timing proxy, not a measured body clock. S uses fixed parameters at the recorded sleep end. Points are scenario midpoints; whiskers are ranges, not confidence intervals. Ranges exclude personal parameter differences; narrowing does not establish individual calibration.")
    modes = {"recent": "近期轨迹（7 天）" if chinese else "Recent trajectory (7 days)", "distribution": "状态分布（所选窗口）" if chinese else "State distribution (selected window)", "circular": "圆周分布（所选窗口）" if chinese else "Circular distribution (selected window)"}
    mode = st.radio("相图读法" if chinese else "Phase chart view", list(modes), format_func=modes.get, index=0 if range_days==7 else 1, key=f"pressure_chart_mode:{range_days}", horizontal=True)
    if mode == "recent":
        st.caption("最近 7 个日历日：日期标出顺序，浅→深为旧→新，菱形为最近可绘制记录；只连接相邻记录日。线表示记录先后，不是日内运动或预测。" if chinese else "Latest 7 calendar days: dates show order, light→dark is older→newer, diamond is the latest plottable record. Only consecutive days connect; lines are observation order, not motion or prediction.")
        figure = build_recent_figure(selected, chinese)
        if figure is not None:
            st.plotly_chart(figure, width="stretch", key="pressure_recent")
        else:
            st.info("最近 7 天没有可绘制点，可查看所选窗口的状态分布。" if chinese else "No plottable points in the last 7 days; see the selected window's state distribution.")
    else:
        occupancy = build_state_occupancy(selected)
        st.caption(f"{occupancy['included_days']} 日参与分布，其中 {occupancy['ambiguous_days']} 日的 S 范围跨格；另有 {occupancy['excluded_phase_days']} 日因相位仅为估计而排除。" if chinese else f"{occupancy['included_days']} days included; {occupancy['ambiguous_days']} have S ranges crossing bins. {occupancy['excluded_phase_days']} estimated-phase days excluded.")
        st.caption("每格 1h × 10 S 单位。颜色深浅表示范围完全落入该格的日数；空心圈表示只有可能覆盖。悬停查看两种计数；可能日数不可跨格相加，也不是概率或停留时长。" if chinese else "Bins: 1h × 10 S units. Color counts days whose entire range lies inside; open circles indicate possible coverage only. Hover for both counts. Possible counts cannot be summed across bins; they are not probabilities or dwell times.")
        if mode == "circular":
            st.caption("目标在上，顺时针延后、逆时针提前，±12h 在下方相接。内圈 S=0，向外压力增大；实心圆越大，确定日数越多。圆点位于格子中心，不是单日观测或拟合线。" if chinese else "Target is at the top; clockwise later, counterclockwise earlier; ±12h meets below. Inner ring S=0; pressure increases outward. Larger filled circles mean more fully-contained days. Points are bin centers, not observations or a fit.")
        if occupancy["included_days"]:
            st.plotly_chart(build_occupancy_figure(occupancy, chinese, polar=mode=="circular"), width="stretch", key=f"pressure_{mode}")
        else:
            st.info("当前窗口没有相位与压力范围均可用的记录；仍可在下方按日期查看已有数据。" if chinese else "No records have both usable phase and pressure ranges; available data remains in the timeline below.")
    st.markdown("**按日期核对变化**" if chinese else "**Check changes over time**")
    st.caption("与所选窗口对应；缺失日、睡眠量未知的相位留空，但可用的压力范围保留。悬停压力点查看模拟时点；波动不能证明周期或吸引子。" if chinese else "Selected window; missing days and phase with unknown sleep duration stay blank, while usable pressure ranges remain. Hover pressure points for modeled timestamps. Fluctuation does not establish a cycle or attractor.")
    st.plotly_chart(build_pressure_timeline(selected, chinese), width="stretch", key="pressure_timeline")
    with st.expander("三维时间轨迹" if chinese else "3D time trajectory"):
        st.caption("第三轴只表示日期；遮挡时可切换正交投影。此图不是三变量动力系统的拟合。" if chinese else "The third axis represents dates. Use orthographic views to resolve occlusion. This is not a fitted three-variable dynamical system.")
        labels = {"oblique": "时间全景" if chinese else "Overview", "phase_pressure": "相位–压力" if chinese else "Phase–pressure", "phase_time": "相位–时间" if chinese else "Phase–time", "pressure_time": "压力–时间" if chinese else "Pressure–time"}
        view = st.radio("观察视角" if chinese else "View", list(labels), format_func=labels.get, horizontal=True)
        figure = build_pressure_figure(selected, chinese, view)
        if figure is not None:
            st.plotly_chart(figure, width="stretch", key="pressure_3d")
    with st.expander("相图如何计算与解释" if chinese else "How to interpret this chart"):
        st.caption("分布以固定参数下的 P 和 S 情景为条件，不代表个体生理真值。重复状态不等于动力学吸引子，图形相关不等于因果；共享睡眠输入本身也会产生相关。" if chinese else "Distribution is conditional on fixed-parameter P and S scenarios, not personal physiological truth. Recurrence is not a dynamical attractor; association is not causation, and shared sleep inputs can create associations.")
        st.markdown("[Haroz et al., 2016 · Connected scatterplots](https://pubmed.ncbi.nlm.nih.gov/26600062/) · [Burgess & Eastman, 2005 · Sleep timing and circadian phase](https://pmc.ncbi.nlm.nih.gov/articles/PMC3841975/) · [Rusterholz et al., 2010 · Individual Process S parameters](https://pmc.ncbi.nlm.nih.gov/articles/PMC2849788/)")
