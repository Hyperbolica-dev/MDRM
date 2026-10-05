import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from model.phase_objective import build_phase_return_frame, calculate_phase_objective, summarize_phase_objective


def build_phase_objective_figure(frame, chinese=False, polar=False):
    valid = frame.dropna(subset=["objective"])
    figure = go.Figure()
    if not polar:
        error_extent = min(12, max(1.5, float(valid["P"].abs().max()) * 1.2)) if not valid.empty else 3
        drift_extent = min(12, max(1.5, float(valid["phase_drift"].abs().max()) * 1.2)) if not valid.empty else 3
        error_grid = np.linspace(-error_extent, error_extent, 97)
        drift_grid = np.linspace(-drift_extent, drift_extent, 97)
        loss = calculate_phase_objective(error_grid[None, :], drift_grid[:, None])
        figure.add_trace(go.Contour(x=error_grid, y=drift_grid, z=loss, contours=dict(start=0, end=1, size=0.02, coloring="heatmap"), zmin=0, zmax=1, colorscale=[[0,"#dbeafe"],[1,"#ffffff"]], showscale=False, line=dict(color="#cbd5e1", width=0.5), hoverinfo="skip", name="J"))
        figure.add_hline(y=0, line_dash="dot", line_color="#64748b")
        figure.add_vline(x=0, line_dash="dot", line_color="#64748b")
    else:
        angles = np.linspace(-180, 180, 145)
        figure.add_trace(go.Scatterpolar(theta=angles, r=np.full(len(angles), 13), mode="lines", line=dict(dash="dot", color="#64748b"), hoverinfo="skip", name="零漂移环" if chinese else "Zero drift"))
    trace_type = go.Scatterpolar if polar else go.Scatter
    goal = dict(theta=[0], r=[13]) if polar else dict(x=[0], y=[0])
    figure.add_trace(trace_type(**goal, mode="markers", marker=dict(symbol="star", size=17, color="#15803d"), name="目标：对齐且不漂移" if chinese else "Target: aligned, no drift"))
    if not valid.empty:
        latest_day = pd.to_datetime(frame["rhythm_day"]).max()
        days = pd.to_datetime(valid["rhythm_day"])
        coords = dict(theta=valid["P"]*15, r=13+valid["phase_drift"]) if polar else dict(x=valid["P"], y=valid["phase_drift"])
        figure.add_trace(trace_type(**coords, mode="markers", marker=dict(size=8, color=(days-latest_day).dt.days, colorscale=[[0,"#94a3b8"],[1,"#2563eb"]]), customdata=list(zip(days.dt.strftime("%Y-%m-%d"), valid["P"], valid["phase_drift"], valid["objective"])), hovertemplate="%{customdata[0]}<br>e=%{customdata[1]:.2f} h<br>v=%{customdata[2]:+.2f} h/day<br>j=%{customdata[3]:.4f}<extra></extra>", name="观测返回状态" if chinese else "Observed return states"))
        recent = valid[days >= latest_day-pd.Timedelta(days=6)]
        line_legend_added = False
        for previous, current in zip(recent.to_dict("records"), recent.to_dict("records")[1:]):
            if (current["rhythm_day"]-previous["rhythm_day"]).days != 1 or abs(current["P"]-previous["P"]) > 12 or abs(current["phase_drift"]-previous["phase_drift"]) > 12:
                continue
            if polar:
                fractions = np.linspace(0, 1, 16)
                segment = dict(theta=15*(previous["P"]+fractions*(current["P"]-previous["P"])), r=13+previous["phase_drift"]+fractions*(current["phase_drift"]-previous["phase_drift"]))
            else:
                segment = dict(x=[previous["P"],current["P"]], y=[previous["phase_drift"],current["phase_drift"]])
            figure.add_trace(trace_type(**segment, mode="lines", line=dict(color="#2563eb", width=2), hoverinfo="skip", name="蓝线：近 7 日实际顺序" if chinese else "Blue line: observed order, last 7 days", showlegend=not line_legend_added))
            line_legend_added = True
        latest = valid.iloc[-1]
        endpoint = dict(theta=[latest["P"]*15], r=[13+latest["phase_drift"]]) if polar else dict(x=[latest["P"]], y=[latest["phase_drift"]])
        figure.add_trace(trace_type(**endpoint, mode="markers+text", text=[pd.Timestamp(latest["rhythm_day"]).strftime("%m-%d")], textposition="top center", marker=dict(symbol="diamond", size=12, color="#f59e0b"), name="最近有效状态" if chinese else "Latest valid state"))
    if polar:
        figure.update_layout(polar=dict(angularaxis=dict(rotation=90, direction="clockwise", tickvals=[0,45,90,135,180,225,270,315], ticktext=["目标 0" if chinese else "Target 0","+3h","+6h","+9h","±12h","−9h","−6h","−3h"]), radialaxis=dict(range=[0,25], tickvals=[1,7,13,19,25], ticktext=["v=−12","−6","0","+6","+12"])))
    else:
        figure.update_xaxes(title_text="相位误差 e（h）：提前 ← 0 → 延后" if chinese else "Phase error e (h): early ← 0 → late", range=[-error_extent,error_extent])
        figure.update_yaxes(title_text="逐日漂移 v（h/day）：负为提前，正为延后" if chinese else "Daily drift v (h/day): negative earlier, positive later", range=[-drift_extent,drift_extent])
    figure.update_layout(height=520, margin=dict(l=50,r=25,t=35,b=45), legend=dict(orientation="h", y=-0.22))
    return figure


def render_phase_objective(points, sleep_need, chinese):
    st.subheader("核心相图：靠近目标，并停止漂移" if chinese else "Core phase portrait: align and stop drifting")
    if points.empty:
        st.info("记录后显示相位误差与逐日漂移；目标是两者同时接近零。" if chinese else "Record sleep to see phase error and daily drift; the goal is for both to approach zero.")
        return
    window = st.radio("优化观察窗口" if chinese else "Objective window", [7,30,90], index=1, horizontal=True)
    days = pd.to_datetime(points["rhythm_day"])
    selected = points[days >= days.max()-pd.Timedelta(days=window-1)]
    frame = build_phase_return_frame(selected)
    report = summarize_phase_objective(frame, sleep_need)
    st.caption("横轴回答离目标多远，纵轴回答每天仍在移动多少。稳定地晚睡、准时但剧烈摆动，都不是目标；星号表示对齐且不再漂移。" if chinese else "Horizontal: distance from target. Vertical: continued day-to-day drift. Stable lateness and volatile timing both miss the target; the star means alignment without drift.")
    st.markdown("**怎么看：** 蓝点越深越新，橙色菱形是最近有效记录；**蓝线只连接近 7 日实际记录，不是预测或推荐路线**。先看离星号有多远，再看是否每天来回移动。" if chinese else "**How to read:** darker blue points are newer; the orange diamond is the latest valid record. **The blue line joins observed days; it is not a forecast or recommended path.** Look at distance from the star, then day-to-day motion.")
    valid = frame.dropna(subset=["objective"])
    if not valid.empty:
        latest = valid.iloc[-1]
        offset, drift = float(latest["P"]), float(latest["phase_drift"])
        columns = st.columns(2)
        columns[0].metric("最近睡眠中点相对目标" if chinese else "Latest sleep midpoint vs target", f"{offset:+.1f} h")
        columns[1].metric("比前一天移动" if chinese else "Change from previous day", f"{drift:+.1f} h")
        if chinese:
            st.info("下一步：先核对左侧目标是否符合你想要的作息，再保持足够睡眠机会。若连续偏晚，优先稳定起床与睡眠安排；若来回摆动，先减少日程反复切换。不要为靠近星号而少睡或通宵。")
            st.caption("为什么会这样？图能说明睡眠时序怎样变化，不能单凭形状判断原因；补觉、助眠药物、日程变化和记录误差都可能参与。最近菱形日期才是本次解读依据，空档不补成轨迹。")
        else:
            st.info("Next: check that the wake target fits your intended routine and preserve enough sleep opportunity. Stabilize the schedule when timing keeps shifting. Do not reduce sleep or stay awake all night to reach the star.")
            st.caption("This shows how sleep timing changed, not why. Recovery sleep, sleep aids, schedule changes and observation error may contribute. Check the date on the latest diamond.")
    view = st.radio("核心相图视角" if chinese else "Core portrait view", ["unwrapped","polar"], format_func=lambda value: ("展开：误差—漂移" if value=="unwrapped" else "圆周：相位—漂移") if chinese else ("Unwrapped: error–drift" if value=="unwrapped" else "Circular: phase–drift"), horizontal=True)
    st.plotly_chart(build_phase_objective_figure(frame, chinese, polar=view=="polar"), width="stretch", key="phase_objective")
    st.caption(("虚线环是零漂移；向内表示逐日提前、向外表示逐日延后，圆心不是目标。" if view=="polar" else "背景是人为定义的目标函数等高线，不是生理势场。") + "近七日连线只表达观测先后；灰→蓝为旧→新，不表示预测或推荐路线。" if chinese else ("The dotted ring means zero drift; inside means earlier each day, outside later. The center is not the target. " if view=="polar" else "Background contours are the designed objective, not a physiological potential. ") + "Latest-seven-day lines show observation order; gray→blue is older→newer, not predictions or recommended routes.")
    if report["sleep_days"]:
        st.caption(f"睡眠约束单独核对：{report['sleep_days']} 日时长已知，中位数 {report['sleep_median']:.2f} h；其中 {report['below_reference_days']} 日低于当前 {sleep_need:.2f} h 参照。不能靠少睡换取较低 J，达到参照也不证明恢复完成。" if chinese else f"Separate sleep check: {report['sleep_days']} known durations, median {report['sleep_median']:.2f} h; {report['below_reference_days']} below the {sleep_need:.2f} h reference. Lower J cannot compensate for insufficient sleep; meeting the reference does not prove recovery.")
    with st.expander("计算依据（可选）" if chinese else "Calculation details (optional)"):
        st.write({key: report[key] for key in ("pairs", "objective", "target_loss", "drift_loss")})
        st.latex(r"v_t=\operatorname{wrap}_{[-12,12)}(e_t-e_{t-1}),\quad \ell(x)=\frac{1-\cos(\pi x/12)}2")
        st.latex(r"j_t=\tfrac12\ell(e_t)+\tfrac12\ell(v_t),\qquad J_W=\operatorname{mean}_{t\in A_W}j_t")
        st.caption("等权是当前设计选择。相位来自睡眠日志代理；漂移是逐日差分，不是日内瞬时速度。真实动力学 F 与干预作用尚未个体识别，因此目标梯度不等于系统将走的方向。S 压力应随睡醒周期变化，不应永久最小化。" if chinese else "Equal weights are a design choice. Phase is a diary proxy; drift is a daily difference, not instantaneous velocity. Individual dynamics F and action effects remain unidentified, so the objective gradient is not a predicted trajectory. Process S should cycle with sleep and wake, not be minimized permanently.")
