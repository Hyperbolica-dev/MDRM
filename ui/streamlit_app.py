import streamlit as st
import pandas as pd
import yaml
import os
import shutil
import importlib
import re
import math
import numpy as np
from datetime import date, datetime, timedelta, timezone
import sys

import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from model import dynamics
from model.empirical_dynamics import system_identification_report
from model.interventions import append_intervention, empty_intervention_frame, load_interventions
from model.learning_data import build_daily_observation_frame
from ui.phase_space import DEFAULT_POLAR_VIEW, daily_target_mask, filter_phase_space_points, latest_plottable_is_current
from model.recommendations import build_recommendation_candidates
dynamics = importlib.reload(dynamics)

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml')
with open(_CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

L = {
    "en": {
        "lang_name": "English",
        "err_import_empty": "Imported file is empty.",
        "err_version_empty": "schema_version column exists but has no usable version values.",
        "err_version_multiple": "schema_version column contains multiple versions. Cannot import.",
        "err_version_unsupported": "Unsupported schema_version: {v}. Only version {current} is accepted.",
        "err_missing_columns": "Missing required columns: {cols}.",
        "err_empty_values": "Imported file contains empty values. Please fill in required fields first.",
        "err_date_format": "date column must use YYYY-MM-DD format.",
        "err_time_format": "{column} column must use HH:MM format.",
        "err_raw_invalid": "Raw data contains empty or unparseable fields. Please correct before saving.",
        "info_no_pd_data": "Not enough data to plot P-D trajectory.",
        "info_no_pd_points": "P-D trajectory is missing plottable state points.",
        "info_no_trend_data": "Not enough data to plot trend charts.",
        "info_no_trend_dates": "Trend charts are missing usable dates.",
        "title": "MRDM Rhythm State Observer",
        "subtitle": "This console tracks the current rhythm state, not just the sleep log.",
        "caption_naps": "Support for naps and split sleep remains, but the interface now centers on the P-D-H state observer.",
        "attractor_settings": "Attractor Settings",
        "attractor_p_limit": "|P| limit (hours)",
        "attractor_d_limit": "D limit (hours)",
        "attractor_heuristic": "These thresholds define formal attractor status and are saved separately from config.yaml.",
        "target_utc_offset": "Target UTC offset",
        "target_utc_offset_help": "UTC offset where the target rhythm is defined. Supports quarter-hour time zones.",
        "dashboard_title": "State Observer Dashboard",
        "metric_p": "P - Phase Offset",
        "metric_d": "D - Sleep Debt",
        "metric_h": "H - Habit Strength",
        "metric_attractor": "Attractor Status",
        "metric_biological_utc": "Estimated Biological UTC",
        "live_title": "Live State (Provisional)",
        "live_caption": "Assumes the user has remained awake since the last recorded wake. These values are not saved.",
        "live_current_time": "Target-local time",
        "live_awake": "Assumed awake",
        "live_missed_sleep": "Missed sleep window",
        "live_projected_debt": "Projected debt",
        "live_no_data": "A recorded wake time is required for live-state estimation.",
        "label_inside": "Inside Attractor",
        "label_outside": "Outside Attractor",
        "info_no_records": "No records yet. Use the daily entry form below to start the observer.",
        "caption_trajectory": "Green = one-day target zone; formal lock still requires 7 consecutive qualifying days. Point color (gray→blue) shows time, the arrow shows the latest step, and gold marks the latest plottable state.",
        "charts_title": "Core Trend Charts",
        "time_range": "Time range",
        "test_panel_title": "Test Panel",
        "test_panel_caption": "Parameters here are for testing and observation only and will NOT be written back to config.yaml. Training and parameter variation are deferred.",
        "test_target_wake": "Target Wake Time",
        "test_sleep_need": "Sleep Need (hours)",
        "test_lambda_d": "lambda_d",
        "test_alpha_up": "alpha_up",
        "test_alpha_down": "alpha_down",
        "test_recovery_k": "Recovery Max (h)",
        "test_recovery_saturation_tau": "Saturation τ",
        "test_reset": "Reset to Defaults",
        "form_date": "Date",
        "form_wake_time": "Wake Time (O1)",
        "form_sleep_time": "Sleep Start (O2)",
        "form_momentum": "Momentum (O3) [0-dysregulated – 10-ideal]",
        "form_disturbance": "Major disturbance (O4) (e.g. all-nighter / illness)",
        "form_medication": "Sleep medication used",
        "form_submit": "Record & Calculate State",
        "submit_success": "Record saved!",
        "submit_state": "**Current state:** Rhythm day {day} | Phase(P): {p}h | Sleep Debt(D): {d}h | Habit Depth(H): {h} | Total sleep: {sleep}h | Sessions: {sessions}",
        "data_mgmt_title": "Raw Data Review & Management",
        "data_mgmt_caption": "For correcting and cleaning raw records. A backup is created before saving and the daily 10-second entry flow is unaffected.",
        "info_no_data": "No raw data yet.",
        "manual_mgmt": "Manual Management",
        "del_col": "Delete",
        "del_help": "Check to delete this raw record",
        "dist_help": "0/1 disturbance flag",
        "med_help": "Whether sleep medication was used",
        "save_button": "Save Raw Data Changes",
        "save_ok": "Changes saved with backup. Latest rhythm day {day} | P={p}h | D={d}h | H={h}",
        "save_fail": "Save failed: {exc}",
        "import_title": "Import records.csv",
        "import_caption": "Validates schema_version, required columns, and date format before importing. A backup of current data is created.",
        "import_uploader": "Choose records.csv to import",
        "import_button": "Import & Overwrite Current Data",
        "import_success": "Import successful, current data updated with backup.",
        "import_fail": "Import validation failed: {exc}",
        "chart_wake": "Wake Time (hour)",
        "chart_sleep_debt": "Sleep Debt D",
        "chart_habit": "Habit Strength H",
        "chart_date": "Date",
        "chart_title": "Core Trend Charts ({range})",
        "diagnosis_insufficient": "Insufficient data",
        "diagnosis_locked": "Inside today's target",
        "diagnosis_jetlag": "Phase delay + sleep debt",
        "diagnosis_deprivation": "Phase advance + sleep debt",
        "diagnosis_advance": "Phase advance",
        "diagnosis_drift": "Phase delay",
        "diagnosis_unknown": "Mixed state",
        "converging": "Moving toward target zone",
        "diverging": "Moving away from target zone",
        "convergence_stable": "Target-zone distance unchanged",
        "convergence_insufficient": "Insufficient movement data",
        "guide_title": "How to read the P-D state space",
        "guide_content": (
            "- **X-axis (P)**: Mid-sleep phase offset. Negative = phase advance; positive = phase delay.\n"
            "- **Y-axis (D)**: Cumulative sleep debt. Lower is better.\n"
            "- **Green rectangle**: A one-day qualifying state, defined by strict $|P|<P_{limit}$ and $D<D_{limit}$ thresholds.\n"
            "- **Filled/open point**: Qualifying day / day outside the target zone.\n"
            "- **Gray→blue**: Older→newer observations. The arrow isolates the latest transition.\n"
            "- **Gold marker**: Latest state with a defined phase estimate.\n\n"
            "**Formal lock differs from position**: `IN ATTRACTOR` requires 7 consecutive qualifying rhythm days. A point can be inside the green zone before formal lock is achieved.\n\n"
            "**Intervention regions**: left/right indicate phase advance/delay; upward indicates more sleep debt. The two upper corners combine phase displacement with elevated debt.\n\n"
            "**Circular view**: Angle = $P$, radius = $D$. Use it to inspect the $-12h/+12h$ seam; use the Cartesian default to compare threshold margins.\n\n"
            "**Light therapy**: CBT_min estimate anchors the light window. Expose to bright light >10000 lux for 30 min within the window to shift $P$ toward attractor."
        ),
        "cbt_min": "Estimated CBT_min",
        "cbt_min_help": "Estimated Core Body Temperature Minimum based on Sleep Midpoint (MSM), serving as the biological anchor for light therapy.",
        "light_window": "Light therapy window",
        "light_window_help": "Expose to bright light for 30 min in this window to actively shift your clock (Recommended: outdoor daylight, bright sunny window, or a light therapy lamp. Regular indoor lamps are insufficient).",
        "light_deadband": "No light therapy needed (within deadband)",
        "light_no_data": "Insufficient data for light therapy guidance",
        "light_uncertain": "Uncertain phase (|P| > 6h). Light therapy is paused.",
        "non_light_guidance": "For the next 3 days: wake within ±30 minutes of the target; keep the intended sleep window dark; avoid bright screens and strong light for 2 hours before sleep; avoid naps longer than 20 minutes or after 15:00; log sleep and wake times daily, then reassess. Do not use intentional bright-light phase shifting while |P| > 6h.",
        "trajectory_range": "Trajectory range",
        "profile_selector": "Profile",
        "profile_personal": "Personal records",
        "profile_stable": "Sample: Stable rhythm",
        "profile_delay": "Sample: Phase delay",
        "profile_debt": "Sample: Sleep debt",
        "profile_advance": "Sample: Phase advance",
        "profile_read_only": "Sample profiles are read-only.",
        "copyright": "© 2026 Hyperbolica-dev · GitHub",
        "observation_title": "Rhythm observation",
        "observation_insufficient": "Observation inconclusive: valid phase data is insufficient.",
        "observation_locked": "Today's P={p}h and D={d}h qualify under the selected thresholds. Formal lock still depends on the consecutive-day streak.",
        "observation_jetlag": "Phase delay and sleep debt are both elevated: stabilize wake time and recover sleep before pursuing a stronger phase shift.",
        "observation_deprivation": "Phase advance and sleep debt are both elevated: prioritize sufficient sleep opportunity and a fixed wake time before phase correction.",
        "observation_advance": "Phase advance is dominant: keep the wake time consistent and avoid extending the schedule earlier until the phase returns toward target.",
        "observation_drift": "Phase delay is dominant while debt remains controlled: preserve the wake anchor and use the light window consistently.",
        "observation_unknown": "The current pattern is mixed: keep wake time stable and collect more consecutive records before changing intervention timing.",
        "habit_observation_title": "Habit observation",
        "habit_wake_consistency": "7-day wake consistency",
        "habit_lock_streak": "Current lock streak",
        "habit_disturbances": "Disturbances in view",
        "habit_trend": "H trend",
        "habit_consistent": "Consistent",
        "habit_variable": "Variable",
        "habit_rising": "Rising",
        "habit_falling": "Falling",
        "habit_stable": "Stable",
        "recovery_title": "Disturbance recovery",
        "recovery_completed": "Latest disturbance recovered in {days} days.",
        "recovery_pending": "Recovery is not complete for the latest disturbance.",
        "recovery_none": "No disturbance recovery interval is available.",
        "non_light_title": "Light paused: phase is uncertain",
        "polar_toggle": "Circular phase view (advanced)",
        "caption_polar_trajectory": "Angle = P and radius = D. This view preserves the -12h/+12h seam but makes rectangular target margins harder to compare.",
        "phase_margin": "Phase threshold margin",
        "debt_margin": "Debt threshold margin",
        "qualifying_streak": "Qualifying streak",
        "streak_help": "Formal lock begins after 7 consecutive qualifying rhythm days.",
        "margin_help": "Positive margin is inside the selected threshold; negative margin is the amount outside.",
        "latest_step": "Latest step: phase {phase_direction} by {phase_delta}h; sleep debt {debt_direction} by {debt_delta}h.",
        "toward_target": "moved toward target",
        "away_from_target": "moved away from target",
        "phase_unchanged": "was unchanged",
        "debt_reduced": "decreased",
        "debt_increased": "increased",
        "debt_unchanged": "was unchanged",
        "current_unplottable": "The current rhythm day ({day}) has no defined phase. The chart marks {latest_day} as the latest plottable state, not the current state.",
        "chart_phase_title": "P-D State-Space Trajectory",
        "chart_p_axis": "P phase (h): advance ← 0 → delay",
        "chart_d_axis": "D sleep debt (h): lower ↓",
        "chart_polar_title": "Circular P-D State-Space Trajectory",
        "zone_target": "Target",
        "zone_delay": "Delay",
        "zone_advance": "Advance",
        "zone_debt": "Debt",
        "zone_compound": "Both",
        "legend_outside": "Outside target (○)",
        "legend_qualifying": "Qualifying (●)",
        "legend_disturbance": "Disturbance (*)",
        "legend_current": "Current",
        "legend_latest_valid": "Latest plottable",
        "empirical_title": "Data-driven Controller (Experimental)",
        "empirical_caption": "Shadow-mode system identification. P is derived from sleep timing, not a direct physiological phase measurement.",
        "empirical_data_status": "1. Data status",
        "empirical_transitions": "Usable one-step transitions",
        "empirical_interventions": "Executed interventions",
        "empirical_action_types": "Observed action types",
        "empirical_validation": "Chronological validation",
        "empirical_yes": "Available",
        "empirical_no": "Unavailable",
        "empirical_none": "None",
        "empirical_model_status": "2. Model status",
        "empirical_variable": "Variable",
        "empirical_persistence": "Persistence error",
        "empirical_learned": "GP error",
        "empirical_beats": "Beats persistence",
        "empirical_forecast": "3. Current one-step forecast",
        "empirical_forecast_caption": "Central estimate ± predictive standard deviation. This is observational forecasting, not an intervention effect.",
        "empirical_forecast_unavailable": "Current forecast unavailable: {reason}",
        "empirical_stage": "4. System identification status",
        "empirical_stage_system_identification": "SYSTEM IDENTIFICATION / DATA COLLECTION",
        "empirical_stage_validated_predictor": "VALIDATED PREDICTOR (OBSERVATIONAL)",
        "empirical_stage_advisory_controller": "ADVISORY CONTROLLER ELIGIBLE",
        "empirical_action_warning": "Action effects are not identifiable: executed intervention variation is insufficient. Candidate actions are hidden.",
        "recommendation_title": "Recommendation draft",
        "recommendation_caption": "This deterministic draft is not an execution record. Review or edit it, then submit explicitly if you carried it out.",
        "recommendation_reason_data": "Data is insufficient; use a conservative stabilization action while collecting records.",
        "recommendation_reason_phase_uncertain": "Phase is outside the safe light range; use stabilization without intentional phase-shifting light.",
        "recommendation_reason_debt": "Sleep debt is above the selected limit; prioritize recovery before phase shifting.",
        "recommendation_reason_phase": "Current phase displacement is within the safe range; the candidate follows the CBT_min light window.",
        "recommendation_reason_maintain": "Phase is inside the deadband; maintain the wake anchor instead of adding phase-shifting light.",
        "recommendation_reason_execution": "Draft recommendation; only explicit submission records execution.",
        "empirical_candidates": "5. Candidate actions",
        "empirical_candidates_hidden": "No candidate ranking is shown until action-conditional prediction beats persistence and the candidate is inside historical execution support.",
        "empirical_log_title": "Record an executed intervention",
        "empirical_log_caption": "Records explicit user-reported execution only. Displayed recommendations are never treated as completed actions.",
        "empirical_action_type": "Action type",
        "empirical_action_day": "Rhythm day",
        "empirical_actual_time": "Actual time",
        "empirical_duration": "Duration minutes (optional)",
        "empirical_notes": "Notes (optional)",
        "empirical_save_action": "Save executed intervention",
        "empirical_action_saved": "Executed intervention saved.",
        "empirical_action_error": "Intervention was not saved: {error}",
        "empirical_beats_yes": "Yes",
        "empirical_beats_no": "No",
        "empirical_predicted_p": "Predicted P",
        "empirical_predicted_d": "Predicted D",
        "empirical_predicted_h": "Predicted H",
        "empirical_current_state": "Current state: P={p}, D={d}, H={h}",
    },
    "cn": {
        "lang_name": "中文",
        "err_import_empty": "导入文件为空。",
        "err_version_empty": "schema_version 列存在，但没有可用的版本值。",
        "err_version_multiple": "schema_version 列包含多个版本值，无法导入。",
        "err_version_unsupported": "不支持的 schema_version: {v}。当前仅接受版本 {current}。",
        "err_missing_columns": "缺少必需列: {cols}。",
        "err_empty_values": "导入文件包含空值，请先补齐必需字段。",
        "err_date_format": "date 列必须使用 YYYY-MM-DD 格式。",
        "err_time_format": "{column} 列必须使用 HH:MM 格式。",
        "err_raw_invalid": "原始数据中存在空值或无法解析的字段，请先修正后再保存。",
        "info_no_pd_data": "当前没有足够的数据绘制 P-D 轨迹。",
        "info_no_pd_points": "P-D 轨迹缺少可绘制的状态点。",
        "info_no_trend_data": "当前没有足够的数据绘制趋势图。",
        "info_no_trend_dates": "趋势图缺少可用日期。",
        "title": "MRDM 节律状态观察器",
        "subtitle": "本控制台追踪当前节律状态，而非单纯的睡眠日志。",
        "caption_naps": "仍支持午睡和分段睡眠，但界面已以 P-D-H 状态观察器为核心。",
        "attractor_settings": "吸引域设置",
        "attractor_p_limit": "|P| 阈值（小时）",
        "attractor_d_limit": "D 阈值（小时）",
        "attractor_heuristic": "这些阈值用于正式吸引子状态判定，并独立于 config.yaml 保存。",
        "target_utc_offset": "目标 UTC 偏移",
        "target_utc_offset_help": "目标节律所在地的 UTC 偏移，支持 15 分钟时区。",
        "dashboard_title": "状态观察仪表盘",
        "metric_p": "P - 相位偏移",
        "metric_d": "D - 睡眠债",
        "metric_h": "H - 习惯强度",
        "metric_attractor": "吸引域状态",
        "metric_biological_utc": "估算生物钟 UTC",
        "live_title": "实时状态（暂估）",
        "live_caption": "假设用户从最后一次记录的醒来时间起持续清醒；这些数值不会保存。",
        "live_current_time": "目标所在地时间",
        "live_awake": "假设清醒时长",
        "live_missed_sleep": "错过睡眠窗口",
        "live_projected_debt": "暂估睡眠债",
        "live_no_data": "需要至少一条起床时间记录才能估算实时状态。",
        "label_inside": "处于吸引域内",
        "label_outside": "处于吸引域外",
        "info_no_records": "尚无记录，请使用下方每日录入表单启动观察器。",
        "caption_trajectory": "绿色区域 = 单日达标区；正式锁定仍需连续 7 个达标日。点颜色（灰→蓝）表示时间，箭头表示最近一步，金色表示最近可绘制状态。",
        "charts_title": "核心趋势图",
        "time_range": "时间范围",
        "test_panel_title": "测试台",
        "test_panel_caption": "这里的参数仅用于测试和观察，不会写回 config.yaml。后续版本再考虑训练和波动化。",
        "test_target_wake": "目标苏醒时间",
        "test_sleep_need": "睡眠需求（小时）",
        "test_lambda_d": "lambda_d",
        "test_alpha_up": "alpha_up",
        "test_alpha_down": "alpha_down",
        "test_recovery_k": "最大恢复量 (h)",
        "test_recovery_saturation_tau": "饱和速率 τ",
        "test_reset": "恢复默认参数",
        "form_date": "日期",
        "form_wake_time": "起床时间 (O1)",
        "form_sleep_time": "睡眠开始时间 (O2)",
        "form_momentum": "动量 (O3) [0-失调 – 10-理想]",
        "form_disturbance": "重大扰动 (O4)（如通宵/疾病）",
        "form_medication": "是否使用助眠药物",
        "form_submit": "记录并计算状态",
        "submit_success": "记录已保存！",
        "submit_state": "**当前状态：** 节律日 {day} | 相位(P)：{p}h | 睡眠债(D)：{d}h | 习惯深度(H)：{h} | 总睡眠：{sleep}h | 睡眠段数：{sessions}",
        "data_mgmt_title": "原始数据审查与管理",
        "data_mgmt_caption": "这里用于纠错和清理原始记录；保存前会先生成备份，不影响日常 10 秒录入流程。",
        "info_no_data": "当前还没有原始数据。",
        "manual_mgmt": "手动管理",
        "del_col": "删除",
        "del_help": "勾选后会删除该条原始记录",
        "dist_help": "0/1 扰动标记",
        "med_help": "是否使用助眠药物",
        "save_button": "保存原始数据修改",
        "save_ok": "已保存修改并生成备份。最新节律日 {day} | P={p}h | D={d}h | H={h}",
        "save_fail": "保存失败：{exc}",
        "import_title": "导入 records.csv",
        "import_caption": "导入前会验证 schema_version、必需列和日期格式；导入成功后会先备份当前数据。",
        "import_uploader": "选择要导入的 records.csv",
        "import_button": "导入并覆盖当前数据",
        "import_success": "导入成功，当前数据已更新并生成备份。",
        "import_fail": "导入校验失败：{exc}",
        "chart_wake": "起床时间（时）",
        "chart_sleep_debt": "睡眠债 D",
        "chart_habit": "习惯强度 H",
        "chart_date": "日期",
        "chart_title": "核心趋势图（{range}）",
        "diagnosis_insufficient": "数据不足",
        "diagnosis_locked": "今日进入目标区",
        "diagnosis_jetlag": "相位延迟 + 睡眠债",
        "diagnosis_deprivation": "相位前移 + 睡眠债",
        "diagnosis_advance": "相位前移",
        "diagnosis_drift": "相位延迟",
        "diagnosis_unknown": "混合状态",
        "converging": "正向目标区靠近",
        "diverging": "正远离目标区",
        "convergence_stable": "与目标区距离未变",
        "convergence_insufficient": "移动数据不足",
        "guide_title": "如何阅读 P-D 状态空间",
        "guide_content": (
            "- **X 轴 (P)**：中睡相位偏移。负值 = 相位前移，正值 = 相位延迟。\n"
            "- **Y 轴 (D)**：累积睡眠债，越低越好。\n"
            "- **绿色矩形**：单日达标区，严格满足 $|P|<P_{limit}$ 且 $D<D_{limit}$。\n"
            "- **实心/空心点**：单日达标 / 位于目标区外。\n"
            "- **灰→蓝**：旧→新观测；箭头单独标出最近一次转移。\n"
            "- **金色标记**：最近一个具有有效相位估算的状态。\n\n"
            "**位置不等于正式锁定**：`IN ATTRACTOR` 需要连续 7 个节律日达标。轨迹点可能已进入绿色区域，但尚未形成正式锁定。\n\n"
            "**干预分区**：左/右分别表示相位前移/延迟，向上表示睡眠债增加；上方两角表示相位偏移与睡眠债叠加。\n\n"
            "**环形视图**：角度 = $P$，半径 = $D$。它适合观察 $-12h/+12h$ 接缝；比较阈值余量时应使用默认直角坐标图。\n\n"
            "**光疗指导**：CBT_min 估算值锚定光疗窗口。在窗口内接触 >10000 lux 强光 30 分钟可将 $P$ 拉回吸引域。"
        ),
        "cbt_min": "估算核心体温最低点 (CBT_min)",
        "cbt_min_help": "基于睡眠中点（MSM）推算的核心体温最低点，是昼夜节律相位的生理锚点，用于自动推算最有效的光疗时间。",
        "light_window": "光疗建议窗口",
        "light_window_help": "在此窗口内接触 30 分钟强光可主动纠正生物钟（推荐：前往户外接触自然光、坐在阳光充足的窗边，或使用专业光疗灯）。注意：普通室内吸顶灯亮度不足。",
        "light_deadband": "无需光疗（位于死区内）",
        "light_no_data": "数据不足，无法生成光疗建议",
        "light_uncertain": "相位不确定（|P| > 6h），暂停光疗建议。",
        "non_light_guidance": "接下来 3 天：起床时间控制在目标时间 ±30 分钟内；计划睡眠窗口保持昏暗；睡前 2 小时避免明亮屏幕和强光；避免超过 20 分钟或 15:00 后的小睡；每天记录睡眠和起床时间，之后重新评估。在 |P| > 6h 时不要使用主动强光移相。",
        "trajectory_range": "轨迹时间范围",
        "profile_selector": "节律档案",
        "profile_personal": "个人记录",
        "profile_stable": "示例：稳定节律",
        "profile_delay": "示例：相位延迟",
        "profile_debt": "示例：睡眠债累积",
        "profile_advance": "示例：相位前移",
        "profile_read_only": "示例档案为只读。",
        "copyright": "© 2026 Hyperbolica-dev · GitHub",
        "observation_title": "节律观察结论",
        "observation_insufficient": "结论暂不明确：有效相位数据不足。",
        "observation_locked": "今日 P={p}h、D={d}h 达到所选阈值；正式锁定仍取决于连续达标日数。",
        "observation_jetlag": "相位延迟与睡眠债均偏高：先固定起床时间并补足睡眠，再进行更强的相位调整。",
        "observation_deprivation": "相位前移与睡眠债均偏高：先保证充足睡眠机会和固定起床时间，再处理相位校正。",
        "observation_advance": "相位前移较突出：保持起床时间一致，在相位回归目标前避免进一步提前作息。",
        "observation_drift": "相位延迟较突出但睡眠债受控：保持起床锚点，并按光疗窗口持续执行。",
        "observation_unknown": "当前模式较混合：保持起床时间稳定，连续记录更多数据后再改变干预时点。",
        "habit_observation_title": "习惯观察",
        "habit_wake_consistency": "近 7 天起床稳定性",
        "habit_lock_streak": "当前锁定连续天数",
        "habit_disturbances": "当前范围内的扰动次数",
        "habit_trend": "H 趋势",
        "habit_consistent": "稳定",
        "habit_variable": "波动",
        "habit_rising": "上升",
        "habit_falling": "下降",
        "habit_stable": "平稳",
        "recovery_title": "扰动恢复",
        "recovery_completed": "最近一次扰动在 {days} 天内恢复。",
        "recovery_pending": "最近一次扰动尚未完成恢复。",
        "recovery_none": "没有可用的扰动恢复区间。",
        "non_light_title": "光疗暂停：相位不确定",
        "polar_toggle": "环形相位视图（进阶）",
        "caption_polar_trajectory": "角度 = P，半径 = D。该视图保留 -12h/+12h 接缝，但不适合比较矩形目标区的阈值余量。",
        "phase_margin": "相位阈值余量",
        "debt_margin": "睡眠债阈值余量",
        "qualifying_streak": "连续达标日",
        "streak_help": "连续 7 个节律日达标后，系统才进入正式锁定。",
        "margin_help": "余量为正表示位于所选阈值内；为负表示超出阈值的量。",
        "latest_step": "最近一步：相位{phase_direction} {phase_delta}h；睡眠债{debt_direction} {debt_delta}h。",
        "toward_target": "向目标靠近",
        "away_from_target": "远离目标",
        "phase_unchanged": "未变化",
        "debt_reduced": "下降",
        "debt_increased": "上升",
        "debt_unchanged": "未变化",
        "current_unplottable": "当前节律日（{day}）没有有效相位估算。图中金色标记是最近可绘制状态 {latest_day}，并非当前状态。",
        "chart_phase_title": "P-D 状态空间轨迹",
        "chart_p_axis": "相位 P（小时）：前移 ← 0 → 延迟",
        "chart_d_axis": "睡眠债 D（小时）：越低越好",
        "chart_polar_title": "环形 P-D 状态空间轨迹",
        "zone_target": "目标",
        "zone_delay": "延迟",
        "zone_advance": "前移",
        "zone_debt": "睡眠债",
        "zone_compound": "叠加",
        "legend_outside": "目标区外（○）",
        "legend_qualifying": "单日达标（●）",
        "legend_disturbance": "扰动（*）",
        "legend_current": "当前",
        "legend_latest_valid": "最近可绘制",
        "empirical_title": "数据驱动控制器（实验）",
        "empirical_caption": "影子模式系统识别。P 来自睡眠时序推导，并非直接生理相位测量。",
        "empirical_data_status": "1. 数据状态",
        "empirical_transitions": "可用一步转移",
        "empirical_interventions": "已执行干预",
        "empirical_action_types": "已观测行动类型",
        "empirical_validation": "时序验证",
        "empirical_yes": "可用",
        "empirical_no": "不可用",
        "empirical_none": "无",
        "empirical_model_status": "2. 模型状态",
        "empirical_variable": "变量",
        "empirical_persistence": "持久性误差",
        "empirical_learned": "GP 误差",
        "empirical_beats": "优于持久性",
        "empirical_forecast": "3. 当前一步预测",
        "empirical_forecast_caption": "中心估计 ± 预测标准差。这是观测预测，不是干预效应。",
        "empirical_forecast_unavailable": "当前预测不可用：{reason}",
        "empirical_stage": "4. 系统识别状态",
        "empirical_stage_system_identification": "系统识别 / 数据收集",
        "empirical_stage_validated_predictor": "已验证预测器（观测性）",
        "empirical_stage_advisory_controller": "具备咨询控制器资格",
        "empirical_action_warning": "行动效应不可识别：实际执行干预缺少变化。候选行动已隐藏。",
        "recommendation_title": "推荐草稿",
        "recommendation_caption": "这是确定性推荐草稿，不是执行记录。请审核或修改，只有明确提交后才会记录实际执行。",
        "recommendation_reason_data": "数据不足：继续收集记录期间，先执行保守的节律稳定行动。",
        "recommendation_reason_phase_uncertain": "相位超出安全光疗范围：采用稳定化行动，不进行主动移相强光照射。",
        "recommendation_reason_debt": "睡眠债超过当前阈值：先恢复睡眠，再进行相位调整。",
        "recommendation_reason_phase": "当前相位偏移处于安全范围：候选时间依据 CBT_min 光疗窗口生成。",
        "recommendation_reason_maintain": "相位处于死区：保持起床锚点，不增加主动移相光疗。",
        "recommendation_reason_execution": "推荐草稿；只有明确提交才会记录实际执行。",
        "empirical_candidates": "5. 候选行动",
        "empirical_candidates_hidden": "仅当行动条件模型优于持久性基线，且候选行动位于历史执行支持范围内时才显示候选比较。",
        "empirical_log_title": "记录已执行干预",
        "empirical_log_caption": "仅记录用户明确报告的实际执行。界面显示的建议绝不视为已完成行动。",
        "empirical_action_type": "行动类型",
        "empirical_action_day": "节律日",
        "empirical_actual_time": "实际时间",
        "empirical_duration": "持续分钟数（可选）",
        "empirical_notes": "备注（可选）",
        "empirical_save_action": "保存已执行干预",
        "empirical_action_saved": "已保存执行干预。",
        "empirical_action_error": "干预未保存：{error}",
        "empirical_beats_yes": "是",
        "empirical_beats_no": "否",
        "empirical_predicted_p": "预测 P",
        "empirical_predicted_d": "预测 D",
        "empirical_predicted_h": "预测 H",
        "empirical_current_state": "当前状态：P={p}，D={d}，H={h}",
    },
}

if "lang" not in st.session_state:
    st.session_state.lang = "en"

def _(key, **kwargs):
    text = L[st.session_state.lang][key]
    if kwargs:
        text = text.format(**kwargs)
    return text

DATA_FILE = "data/records.csv"
BACKUP_DIR = "data/backups"
UI_SETTINGS_FILE = "data/ui_settings.yaml"
PROFILE_DIR = "data/profiles"
PROFILE_IDS = ("personal", "stable", "delay", "debt", "advance")
SAMPLE_PROFILE_IDS = PROFILE_IDS[1:]
CURRENT_SCHEMA_VERSION = 1
ATTRACTOR_DAYS = 7
BACKUP_RETENTION_COUNT = 30
RAW_COLUMNS = ["date", "wake_time", "sleep_time", "momentum", "disturbance", "sleep_medication"]
META_COLUMNS = ["schema_version"]
DERIVED_COLUMNS = ["P", "D", "H", "in_attractor"]
PREFERRED_COLUMNS = META_COLUMNS + RAW_COLUMNS + DERIVED_COLUMNS
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")

if not os.path.exists("data"):
    os.makedirs("data")
if not os.path.exists(DATA_FILE):
    df_init = pd.DataFrame(columns=[
        "schema_version",
        "date", "wake_time", "sleep_time", "momentum", "disturbance", "sleep_medication",
        "P", "D", "H", "in_attractor"
    ])
    df_init.to_csv(DATA_FILE, index=False)


def get_empty_records_frame():
    return pd.DataFrame(columns=PREFERRED_COLUMNS)
def load_ui_settings():
    defaults = {
        "attractor_p_limit": 1.0,
        "attractor_d_limit": 5.0,
        "target_utc_offset": 0.0,
        "profile_id": "personal",
    }
    if not os.path.exists(UI_SETTINGS_FILE):
        return defaults
    try:
        with open(UI_SETTINGS_FILE, "r") as settings_file:
            loaded = yaml.safe_load(settings_file) or {}
        p_limit = float(loaded.get("attractor_p_limit", defaults["attractor_p_limit"]))
        d_limit = float(loaded.get("attractor_d_limit", defaults["attractor_d_limit"]))
        target_utc_offset = float(loaded.get("target_utc_offset", defaults["target_utc_offset"]))
        profile_id = str(loaded.get("profile_id", defaults["profile_id"]))
        if not math.isfinite(p_limit) or not 0.1 <= p_limit <= 12.0:
            p_limit = defaults["attractor_p_limit"]
        if not math.isfinite(d_limit) or not 0.1 <= d_limit <= 24.0:
            d_limit = defaults["attractor_d_limit"]
        if not math.isfinite(target_utc_offset) or not -12.0 <= target_utc_offset <= 14.0:
            target_utc_offset = defaults["target_utc_offset"]
        if profile_id not in PROFILE_IDS:
            profile_id = defaults["profile_id"]
        return {
            "attractor_p_limit": p_limit,
            "attractor_d_limit": d_limit,
            "target_utc_offset": target_utc_offset,
            "profile_id": profile_id,
        }
    except (OSError, TypeError, ValueError, yaml.YAMLError):
        return defaults


def save_ui_settings(attractor_p_limit: float, attractor_d_limit: float, target_utc_offset: float, profile_id: str = "personal"):
    if profile_id not in PROFILE_IDS:
        profile_id = "personal"
    os.makedirs(os.path.dirname(UI_SETTINGS_FILE), exist_ok=True)
    with open(UI_SETTINGS_FILE, "w") as settings_file:
        yaml.safe_dump(
            {
                "attractor_p_limit": float(attractor_p_limit),
                "attractor_d_limit": float(attractor_d_limit),
                "target_utc_offset": float(target_utc_offset),
                "profile_id": profile_id,
            },
            settings_file,
            sort_keys=True,
        )


def format_utc_offset(offset: float | None) -> str:
    if offset is None or pd.isna(offset):
        return "N/A"
    total_minutes = int(round(float(offset) * 60))
    sign = "+" if total_minutes >= 0 else "-"
    absolute_minutes = abs(total_minutes)
    hours, minutes = divmod(absolute_minutes, 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def ensure_schema_version_column(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    if "schema_version" not in normalized.columns:
        normalized["schema_version"] = CURRENT_SCHEMA_VERSION
    normalized["schema_version"] = pd.to_numeric(normalized["schema_version"], errors="coerce")
    normalized["schema_version"] = normalized["schema_version"].fillna(CURRENT_SCHEMA_VERSION).astype(int)
    return normalized


def keep_recent_backups(backup_dir: str = BACKUP_DIR, retention_count: int = BACKUP_RETENTION_COUNT):
    if not os.path.exists(backup_dir):
        return
    backup_files = sorted(
        [
            os.path.join(backup_dir, name)
            for name in os.listdir(backup_dir)
            if name.startswith("records_backup_") and name.endswith(".csv")
        ],
        key=lambda path: os.path.getmtime(path),
        reverse=True,
    )
    for path in backup_files[retention_count:]:
        try:
            os.remove(path)
        except OSError:
            pass


def ensure_daily_backup(data_file: str = DATA_FILE):
    if not os.path.exists(data_file):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    today_tag = datetime.now().strftime("%Y%m%d")
    existing_today = [
        name for name in os.listdir(BACKUP_DIR)
        if name.startswith("records_backup_") and name.endswith(".csv")
    ]
    if existing_today:
        return
    backup_name = datetime.now().strftime("records_backup_%Y%m%d_%H%M%S.csv")
    shutil.copy2(data_file, os.path.join(BACKUP_DIR, backup_name))
    keep_recent_backups()


def validate_date_string(value: str) -> bool:
    return bool(DATE_PATTERN.match(str(value)))


def validate_time_string(value: str) -> bool:
    return bool(TIME_PATTERN.match(str(value)))


def validate_import_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError(_("err_import_empty"))

    working = df.copy()
    if "schema_version" in working.columns:
        version_values = pd.to_numeric(working["schema_version"], errors="coerce").dropna().astype(int).unique().tolist()
        if not version_values:
            raise ValueError(_("err_version_empty"))
        if len(version_values) > 1:
            raise ValueError(_("err_version_multiple"))
        if version_values[0] != CURRENT_SCHEMA_VERSION:
            raise ValueError(_("err_version_unsupported", v=version_values[0], current=CURRENT_SCHEMA_VERSION))
    else:
        working["schema_version"] = CURRENT_SCHEMA_VERSION

    missing_columns = [column for column in RAW_COLUMNS if column not in working.columns]
    if missing_columns:
        raise ValueError(_("err_missing_columns", cols=", ".join(missing_columns)))

    required_values = working[RAW_COLUMNS].copy()
    if required_values.isna().any().any():
        raise ValueError(_("err_empty_values"))

    invalid_dates = [value for value in required_values["date"].astype(str).tolist() if not validate_date_string(value)]
    if invalid_dates:
        raise ValueError(_("err_date_format"))

    for column in ["wake_time", "sleep_time"]:
        invalid_times = [value for value in required_values[column].astype(str).tolist() if not validate_time_string(value)]
        if invalid_times:
            raise ValueError(_("err_time_format", column=column))

    normalized = normalize_raw_records(working[RAW_COLUMNS])
    normalized = ensure_schema_version_column(normalized)
    return normalized


def write_records_frame(df: pd.DataFrame, path: str = DATA_FILE):
    output = ensure_schema_version_column(df.copy())
    for column in PREFERRED_COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA
    output = output[PREFERRED_COLUMNS]
    output.to_csv(path, index=False)


def load_records_frame(path: str = DATA_FILE):
    if not os.path.exists(path):
        return get_empty_records_frame()

    df = pd.read_csv(path)
    for column in PREFERRED_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA
    return df[PREFERRED_COLUMNS]


def profile_data_path(profile_id: str):
    if profile_id == "personal":
        return DATA_FILE
    return os.path.join(PROFILE_DIR, f"{profile_id}.csv")


def profile_clock(minutes: int):
    hours, remainder = divmod(minutes, 60)
    return f"{hours % 24:02d}:{remainder:02d}"


def build_sample_profile(profile_id: str):
    first_day = date.today() - timedelta(days=41)
    rows = []
    for index in range(42):
        current_date = first_day + timedelta(days=index)
        if profile_id == "stable":
            sleep_minutes, wake_minutes = 60, 510
            momentum, disturbance, medication = 9, 0, False
        elif profile_id == "delay":
            sleep_minutes = 180 + index * 8
            wake_minutes = 660 + index * 8
            momentum, disturbance, medication = 6, int(index in {12, 25}), False
        elif profile_id == "advance":
            sleep_minutes, wake_minutes = 1350, 390
            momentum, disturbance, medication = 7, int(index in {8, 21, 34}), False
        else:
            sleep_minutes = 210 if index % 3 == 0 else 150
            wake_minutes = 480 if index % 3 == 0 else 510
            momentum, disturbance, medication = 3, int(index % 5 == 0), bool(index % 11 == 0)
        rows.append(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "date": current_date,
                "wake_time": profile_clock(wake_minutes),
                "sleep_time": profile_clock(sleep_minutes),
                "momentum": momentum,
                "disturbance": disturbance,
                "sleep_medication": medication,
            }
        )
    return pd.DataFrame(rows)


def ensure_profile_samples():
    os.makedirs(PROFILE_DIR, exist_ok=True)
    for profile_id in SAMPLE_PROFILE_IDS:
        path = profile_data_path(profile_id)
        if not os.path.exists(path):
            write_records_frame(build_sample_profile(profile_id), path)

def normalize_raw_records(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()

    if normalized.empty:
        return pd.DataFrame(columns=RAW_COLUMNS)

    for column in RAW_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = pd.NA

    normalized = normalized[RAW_COLUMNS].copy()
    normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce").dt.date
    normalized["wake_time"] = normalized["wake_time"].astype(str).str.strip()
    normalized["sleep_time"] = normalized["sleep_time"].astype(str).str.strip()
    normalized["momentum"] = pd.to_numeric(normalized["momentum"], errors="coerce")
    normalized["disturbance"] = pd.to_numeric(normalized["disturbance"], errors="coerce")
    normalized["sleep_medication"] = normalized["sleep_medication"].fillna(False).astype(bool)

    if normalized[["date", "wake_time", "sleep_time", "momentum", "disturbance"]].isna().any().any():
        raise ValueError(_("err_raw_invalid"))

    normalized["date"] = normalized["date"].astype(str)
    normalized["momentum"] = normalized["momentum"].astype(int)
    normalized["disturbance"] = normalized["disturbance"].astype(int)
    return normalized


def rebuild_persisted_records(raw_df: pd.DataFrame, params: dict):
    normalized = normalize_raw_records(raw_df)
    normalized = ensure_schema_version_column(normalized)
    summary, derived = dynamics.calculate_daily_state(
        normalized,
        params["target_wake"],
        params["sleep_need_hours"],
        params["lambda_d"],
        params["alpha_up"],
        params["alpha_down"],
        params["recovery_k"],
        params["recovery_saturation_tau"],
        params["attractor_p_limit"],
        params["attractor_d_limit"],
        ATTRACTOR_DAYS,
    )
    daily_summary = dynamics.build_daily_summary_frame(
        derived,
        params["target_wake"],
        params["sleep_need_hours"],
        params["lambda_d"],
        params["alpha_up"],
        params["alpha_down"],
        params["recovery_k"],
        params["recovery_saturation_tau"],
        params["attractor_p_limit"],
        params["attractor_d_limit"],
        ATTRACTOR_DAYS,
    )

    if derived.empty:
        persisted = normalized.copy()
        for column in DERIVED_COLUMNS:
            persisted[column] = pd.NA
        return summary, derived, daily_summary, persisted[PREFERRED_COLUMNS]

    derived_view = derived.copy()
    if not daily_summary.empty:
        state_by_day = daily_summary[["rhythm_day", "P", "D", "H", "in_attractor"]]
        derived_view = derived_view.merge(state_by_day, on="rhythm_day", how="left", suffixes=("", "_day"))
        for column in DERIVED_COLUMNS:
            if f"{column}_day" in derived_view.columns:
                derived_view[column] = derived_view[f"{column}_day"]

    derived_view = ensure_schema_version_column(derived_view)
    persisted = derived_view[PREFERRED_COLUMNS].copy()
    return summary, derived, daily_summary, persisted


def save_records_frame(df: pd.DataFrame, create_backup: bool = False, path: str = DATA_FILE):
    if create_backup and os.path.exists(path):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        backup_name = datetime.now().strftime("records_backup_%Y%m%d_%H%M%S.csv")
        shutil.copy2(path, os.path.join(BACKUP_DIR, backup_name))
        keep_recent_backups()

    write_records_frame(df, path)


def get_daily_state_frames(records_frame: pd.DataFrame, params: dict):
    if records_frame.empty:
        empty = pd.DataFrame()
        return empty, empty, empty

    daily_view = dynamics.derive_session_frame(records_frame, params["target_wake"])
    daily_summary = dynamics.build_daily_summary_frame(
        daily_view,
        params["target_wake"],
        params["sleep_need_hours"],
        params["lambda_d"],
        params["alpha_up"],
        params["alpha_down"],
        params["recovery_k"],
        params["recovery_saturation_tau"],
        params["attractor_p_limit"],
        params["attractor_d_limit"],
        ATTRACTOR_DAYS,
    )

    if daily_summary.empty:
        return daily_view, daily_summary, pd.DataFrame()

    summary_lookup = daily_summary.set_index("rhythm_day")
    daily_points_rows = []
    for rhythm_day in daily_summary["rhythm_day"].tolist():
        current_bucket = daily_view[daily_view["main_sleep_day"] == rhythm_day]
        if current_bucket.empty:
            representative = pd.Series({
                "rhythm_day": rhythm_day,
                "wake_time": "N/A",
                "momentum": pd.NA,
                "disturbance": 0,
            })
        else:
            main_sleep_bucket = current_bucket[current_bucket["is_main_sleep"]]
            if not main_sleep_bucket.empty:
                representative = main_sleep_bucket.sort_values(["sleep_hours", "row_order"], ascending=[False, False]).iloc[0]
            else:
                representative = current_bucket.sort_values(["sleep_hours", "row_order"], ascending=[False, False]).iloc[0]
        point_row = representative.copy()
        for column in ["P", "D", "H", "in_attractor", "disturbance", "recovery_days", "sleep_hours", "session_count"]:
            point_row[column] = summary_lookup.loc[rhythm_day, column]
        daily_points_rows.append(point_row)

    daily_points = pd.DataFrame(daily_points_rows).sort_values("rhythm_day")
    return daily_view, daily_summary, daily_points
@st.cache_data(show_spinner=False)
def build_empirical_status_report(daily_summary_frame, daily_view_frame, intervention_frame):
    daily_observations = build_daily_observation_frame(daily_summary_frame, daily_view_frame)
    return system_identification_report(daily_observations, intervention_frame)






def build_phase_space_context(daily_points: pd.DataFrame, p_limit: float, d_limit: float):
    if daily_points.empty:
        return None
    ordered = daily_points.copy().sort_values("rhythm_day")
    ordered["rhythm_day"] = pd.to_datetime(ordered["rhythm_day"], errors="coerce")
    ordered["P"] = pd.to_numeric(ordered["P"], errors="coerce")
    ordered["D"] = pd.to_numeric(ordered["D"], errors="coerce")
    ordered = ordered.dropna(subset=["rhythm_day"])
    if ordered.empty:
        return None
    qualifying = ordered["P"].notna() & ordered["D"].notna() & (ordered["P"].abs() < p_limit) & (ordered["D"] < d_limit)
    streak = 0
    for is_qualifying in qualifying.iloc[::-1]:
        if not bool(is_qualifying):
            break
        streak += 1
    valid = ordered.dropna(subset=["P", "D"])
    latest = ordered.iloc[-1]
    context = {
        "current_day": latest["rhythm_day"],
        "current_plottable": pd.notna(latest["P"]) and pd.notna(latest["D"]),
        "latest_valid_day": valid.iloc[-1]["rhythm_day"] if not valid.empty else None,
        "streak": streak,
        "phase_margin": None,
        "debt_margin": None,
        "phase_progress": None,
        "debt_progress": None,
    }
    if not context["current_plottable"]:
        return context
    context["phase_margin"] = p_limit - abs(float(latest["P"]))
    context["debt_margin"] = d_limit - float(latest["D"])
    if len(ordered) >= 2:
        previous = ordered.iloc[-2]
        if pd.notna(previous["P"]) and pd.notna(previous["D"]):
            context["phase_progress"] = abs(float(previous["P"])) - abs(float(latest["P"]))
            context["debt_progress"] = float(previous["D"]) - float(latest["D"])
    return context


def render_phase_space_context(daily_points: pd.DataFrame, p_limit: float, d_limit: float):
    context = build_phase_space_context(daily_points, p_limit, d_limit)
    if context is None:
        return
    if not context["current_plottable"]:
        latest_day = context["latest_valid_day"]
        if latest_day is not None:
            st.warning(_(
                "current_unplottable",
                day=context["current_day"].strftime("%Y-%m-%d"),
                latest_day=latest_day.strftime("%Y-%m-%d"),
            ))
        return
    phase_col, debt_col, streak_col = st.columns(3)
    phase_col.metric(_("phase_margin"), f"{context['phase_margin']:+.2f} h", help=_("margin_help"))
    debt_col.metric(_("debt_margin"), f"{context['debt_margin']:+.2f} h", help=_("margin_help"))
    streak_col.metric(_("qualifying_streak"), f"{context['streak']} d", help=_("streak_help"))
    if context["phase_progress"] is None or context["debt_progress"] is None:
        return
    phase_progress = context["phase_progress"]
    debt_progress = context["debt_progress"]
    if math.isclose(phase_progress, 0.0, abs_tol=0.005):
        phase_direction = _("phase_unchanged")
    elif phase_progress > 0:
        phase_direction = _("toward_target")
    else:
        phase_direction = _("away_from_target")
    if math.isclose(debt_progress, 0.0, abs_tol=0.005):
        debt_direction = _("debt_unchanged")
    elif debt_progress > 0:
        debt_direction = _("debt_reduced")
    else:
        debt_direction = _("debt_increased")
    st.caption(_(
        "latest_step",
        phase_direction=phase_direction,
        phase_delta=f"{abs(phase_progress):.2f}",
        debt_direction=debt_direction,
        debt_delta=f"{abs(debt_progress):.2f}",
    ))



def draw_state_trajectory(daily_points: pd.DataFrame, attractor_p_limit: float, attractor_d_limit: float):
    if daily_points.empty:
        st.info(_("info_no_pd_data"))
        return

    ordered = daily_points.copy().sort_values("rhythm_day")
    ordered["rhythm_day"] = pd.to_datetime(ordered["rhythm_day"], errors="coerce")
    latest_day = ordered["rhythm_day"].max()
    plot_frame = ordered.dropna(subset=["P", "D", "rhythm_day"]).copy()
    if plot_frame.empty:
        st.info(_("info_no_pd_points"))
        return

    qualifying_mask = daily_target_mask(plot_frame, attractor_p_limit, attractor_d_limit)
    p_vals = plot_frame["P"].to_numpy()
    d_vals = plot_frame["D"].to_numpy()
    n = len(plot_frame)
    indices = np.arange(n)
    latest_is_current = latest_plottable_is_current(ordered, plot_frame)
    colorscale = [[0.0, "#9ca3af"], [1.0, "#2563eb"]]

    max_p = max(float(np.abs(p_vals).max()), attractor_p_limit, 3.0)
    x_pad = max_p * 1.15
    max_d = max(float(d_vals.max()), attractor_d_limit, 8.0)
    y_pad = max_d * 1.15
    fig = go.Figure()

    fig.add_shape(type="rect", x0=attractor_p_limit, y0=0, x1=x_pad, y1=attractor_d_limit,
                  fillcolor="#fff3cd", opacity=0.07, layer="below", line_width=0)
    fig.add_shape(type="rect", x0=-x_pad, y0=0, x1=-attractor_p_limit, y1=attractor_d_limit,
                  fillcolor="#d1ecf1", opacity=0.07, layer="below", line_width=0)
    fig.add_shape(type="rect", x0=-attractor_p_limit, y0=attractor_d_limit, x1=attractor_p_limit, y1=y_pad,
                  fillcolor="#f8d7da", opacity=0.07, layer="below", line_width=0)
    fig.add_shape(type="rect", x0=attractor_p_limit, y0=attractor_d_limit, x1=x_pad, y1=y_pad,
                  fillcolor="#f5c6cb", opacity=0.07, layer="below", line_width=0)
    fig.add_shape(type="rect", x0=-x_pad, y0=attractor_d_limit, x1=-attractor_p_limit, y1=y_pad,
                  fillcolor="#f5c6cb", opacity=0.07, layer="below", line_width=0)
    fig.add_shape(type="rect", x0=-attractor_p_limit, y0=0, x1=attractor_p_limit, y1=attractor_d_limit,
                  fillcolor="#cfead4", opacity=0.35, layer="below",
                  line=dict(color="#4a7d57", dash="dash", width=1.5))

    zone_labels = [
        (0, attractor_d_limit * 0.5, _("zone_target")),
        ((attractor_p_limit + x_pad) / 2.0, attractor_d_limit * 0.5, _("zone_delay")),
        ((-x_pad - attractor_p_limit) / 2.0, attractor_d_limit * 0.5, _("zone_advance")),
        (0, (attractor_d_limit + y_pad) / 2.0, _("zone_debt")),
        ((attractor_p_limit + x_pad) / 2.0, (attractor_d_limit + y_pad) / 2.0, _("zone_compound")),
        ((-x_pad - attractor_p_limit) / 2.0, (attractor_d_limit + y_pad) / 2.0, _("zone_compound")),
    ]
    for zone_x, zone_y, zone_text in zone_labels:
        fig.add_annotation(
            x=zone_x, y=zone_y, text=zone_text, showarrow=False,
            font=dict(size=10, color="#666666"), opacity=0.8,
        )

    fig.add_trace(go.Scatter(
        x=p_vals,
        y=d_vals,
        mode="lines",
        line=dict(color="#9ca3af", width=1.5),
        showlegend=False,
        hoverinfo="skip",
    ))
    tail = plot_frame.tail(7)
    fig.add_trace(go.Scatter(
        x=tail["P"],
        y=tail["D"],
        mode="lines",
        line=dict(color="#4b5563", width=2.5),
        showlegend=False,
        hoverinfo="skip",
    ))
    if n >= 2:
        fig.add_annotation(
            x=p_vals[-1], y=d_vals[-1], ax=p_vals[-2], ay=d_vals[-2],
            xref="x", yref="y", axref="x", ayref="y",
            arrowhead=2, arrowsize=1.0, arrowwidth=1.8,
            arrowcolor="#374151", showarrow=True, text="",
        )

    tooltip_cols = ["H", "wake_time", "sleep_hours", "momentum", "disturbance"]
    common_hover = (
        "<b>%{text}</b><br>P: %{x:.2f} h<br>D: %{y:.2f} h<br>"
        "H: %{customdata[0]:.3f}<br>Wake: %{customdata[1]}<br>"
        "Sleep: %{customdata[2]:.1f} h<br>Momentum: %{customdata[3]}<br>"
        "Disturbance: %{customdata[4]}<extra></extra>"
    )

    outside_mask = (~qualifying_mask).to_numpy()
    if np.any(outside_mask):
        outside = plot_frame[~qualifying_mask]
        fig.add_trace(go.Scatter(
            x=outside["P"],
            y=outside["D"],
            mode="markers",
            marker=dict(
                symbol="circle-open",
                size=9,
                color=indices[outside_mask],
                colorscale=colorscale,
                cmin=0,
                cmax=max(n - 1, 1),
                showscale=False,
                opacity=0.9,
                line=dict(width=1.5),
            ),
            name=_("legend_outside"),
            hovertemplate=common_hover,
            text=outside["rhythm_day"].dt.strftime("%Y-%m-%d"),
            customdata=outside[tooltip_cols].to_numpy(),
        ))

    qualifying_values = qualifying_mask.to_numpy()
    if np.any(qualifying_values):
        qualifying_points = plot_frame[qualifying_mask]
        fig.add_trace(go.Scatter(
            x=qualifying_points["P"],
            y=qualifying_points["D"],
            mode="markers",
            marker=dict(
                symbol="circle",
                size=9,
                color=indices[qualifying_values],
                colorscale=colorscale,
                cmin=0,
                cmax=max(n - 1, 1),
                showscale=False,
                opacity=0.9,
                line=dict(color="#1f2937", width=1.0),
            ),
            name=_("legend_qualifying"),
            hovertemplate=common_hover,
            text=qualifying_points["rhythm_day"].dt.strftime("%Y-%m-%d"),
            customdata=qualifying_points[tooltip_cols].to_numpy(),
        ))

    disturbance_mask = plot_frame["disturbance"].fillna(0).astype(bool).to_numpy()
    if np.any(disturbance_mask):
        disturbance_points = plot_frame[disturbance_mask]
        fig.add_trace(go.Scatter(
            x=disturbance_points["P"],
            y=disturbance_points["D"],
            mode="markers",
            marker=dict(symbol="star", size=13, color="#e76f51", line=dict(color="#7f1d1d", width=1.2)),
            name=_("legend_disturbance"),
            hovertemplate="<b>%{text}</b><br>Recovery: %{customdata[0]} days<extra></extra>",
            text=disturbance_points["rhythm_day"].dt.strftime("%Y-%m-%d"),
            customdata=disturbance_points[["recovery_days"]].fillna("Unavailable").to_numpy(),
        ))
    recovery_points = plot_frame[plot_frame["recovery_days"].notna()]
    for recovery_index, point in recovery_points.iterrows():
        fig.add_annotation(
            x=point["P"], y=point["D"], text=f"R={int(point['recovery_days'])}d",
            showarrow=False, yshift=14, font=dict(size=10, color="#7f1d1d"),
        )

    latest = plot_frame.iloc[-1]
    latest_name = _("legend_current") if latest_is_current else _("legend_latest_valid")
    fig.add_trace(go.Scatter(
        x=[latest["P"]],
        y=[latest["D"]],
        mode="markers",
        marker=dict(color="#ffb703", size=15, line=dict(color="#1f2937", width=1.5), symbol="circle", opacity=0.95),
        name=latest_name,
        hovertemplate=common_hover,
        text=[latest["rhythm_day"].strftime("%Y-%m-%d")],
        customdata=latest[tooltip_cols].to_numpy().reshape(1, -1),
    ))

    fig.update_layout(
        title=dict(text=_("chart_phase_title"), x=0.02, xanchor="left", font=dict(color="#e5e7eb", size=18)),
        xaxis_title=_("chart_p_axis"),
        yaxis_title=_("chart_d_axis"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0, font=dict(size=10)),
        hovermode="closest",
        height=580,
        margin=dict(l=70, r=15, t=60, b=110),
    )
    fig.update_xaxes(zeroline=True, zerolinecolor="#9ca3af", zerolinewidth=1, range=[-x_pad, x_pad])
    fig.update_yaxes(zeroline=True, zerolinecolor="#9ca3af", zerolinewidth=1, range=[0, y_pad])
    st.plotly_chart(fig, width="stretch")




def draw_polar_state_trajectory(daily_points: pd.DataFrame, attractor_p_limit: float, attractor_d_limit: float):
    if daily_points.empty:
        st.info(_("info_no_pd_data"))
        return

    ordered = daily_points.copy().sort_values("rhythm_day")
    ordered["rhythm_day"] = pd.to_datetime(ordered["rhythm_day"], errors="coerce")
    latest_day = ordered["rhythm_day"].max()
    plot_frame = ordered.dropna(subset=["P", "D", "rhythm_day"]).copy()
    if plot_frame.empty:
        st.info(_("info_no_pd_points"))
        return

    qualifying_mask = daily_target_mask(plot_frame, attractor_p_limit, attractor_d_limit)
    theta_vals = plot_frame["P"].to_numpy() * 15.0
    radial_vals = plot_frame["D"].to_numpy()
    n = len(plot_frame)
    indices = np.arange(n)
    latest_is_current = latest_plottable_is_current(ordered, plot_frame)
    colorscale = [[0.0, "#9ca3af"], [1.0, "#2563eb"]]
    fig = go.Figure()

    target_theta = np.linspace(-attractor_p_limit * 15.0, attractor_p_limit * 15.0, 40)
    target_radius = np.full_like(target_theta, attractor_d_limit)
    target_theta = np.concatenate([target_theta, target_theta[::-1]])
    target_radius = np.concatenate([target_radius, np.zeros(40)])
    fig.add_trace(go.Scatterpolar(
        theta=target_theta.tolist(),
        r=target_radius.tolist(),
        fill="toself",
        fillcolor="#cfead4",
        opacity=0.35,
        line=dict(color="#4a7d57", dash="dash", width=1.5),
        showlegend=False,
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatterpolar(
        theta=theta_vals,
        r=radial_vals,
        mode="lines",
        line=dict(color="#9ca3af", width=1.5),
        showlegend=False,
        hoverinfo="skip",
    ))
    tail = plot_frame.tail(7)
    fig.add_trace(go.Scatterpolar(
        theta=tail["P"].to_numpy() * 15.0,
        r=tail["D"],
        mode="lines",
        line=dict(color="#4b5563", width=2.5),
        showlegend=False,
        hoverinfo="skip",
    ))

    tooltip_cols = ["P", "H", "wake_time", "sleep_hours", "momentum", "disturbance"]
    common_hover = (
        "<b>%{text}</b><br>P: %{customdata[0]:.2f} h<br>D: %{r:.2f} h<br>"
        "H: %{customdata[1]:.3f}<br>Wake: %{customdata[2]}<br>"
        "Sleep: %{customdata[3]:.1f} h<br>Momentum: %{customdata[4]}<br>"
        "Disturbance: %{customdata[5]}<extra></extra>"
    )

    outside_mask = (~qualifying_mask).to_numpy()
    if np.any(outside_mask):
        outside = plot_frame[~qualifying_mask]
        fig.add_trace(go.Scatterpolar(
            theta=outside["P"].to_numpy() * 15.0,
            r=outside["D"],
            mode="markers",
            marker=dict(
                symbol="circle-open",
                size=9,
                color=indices[outside_mask],
                colorscale=colorscale,
                cmin=0,
                cmax=max(n - 1, 1),
                showscale=False,
                opacity=0.9,
                line=dict(width=1.5),
            ),
            name=_("legend_outside"),
            hovertemplate=common_hover,
            text=outside["rhythm_day"].dt.strftime("%Y-%m-%d"),
            customdata=outside[tooltip_cols].to_numpy(),
        ))

    qualifying_values = qualifying_mask.to_numpy()
    if np.any(qualifying_values):
        qualifying_points = plot_frame[qualifying_mask]
        fig.add_trace(go.Scatterpolar(
            theta=qualifying_points["P"].to_numpy() * 15.0,
            r=qualifying_points["D"],
            mode="markers",
            marker=dict(
                symbol="circle",
                size=9,
                color=indices[qualifying_values],
                colorscale=colorscale,
                cmin=0,
                cmax=max(n - 1, 1),
                showscale=False,
                opacity=0.9,
                line=dict(color="#1f2937", width=1.0),
            ),
            name=_("legend_qualifying"),
            hovertemplate=common_hover,
            text=qualifying_points["rhythm_day"].dt.strftime("%Y-%m-%d"),
            customdata=qualifying_points[tooltip_cols].to_numpy(),
        ))

    disturbance_mask = plot_frame["disturbance"].fillna(0).astype(bool).to_numpy()
    if np.any(disturbance_mask):
        disturbance_points = plot_frame[disturbance_mask]
        fig.add_trace(go.Scatterpolar(
            theta=disturbance_points["P"].to_numpy() * 15.0,
            r=disturbance_points["D"],
            mode="markers",
            marker=dict(symbol="star", size=13, color="#e76f51", line=dict(color="#7f1d1d", width=1.2)),
            name=_("legend_disturbance"),
            hovertemplate="<b>%{text}</b><br>Recovery: %{customdata[0]} days<extra></extra>",
            text=disturbance_points["rhythm_day"].dt.strftime("%Y-%m-%d"),
            customdata=disturbance_points[["recovery_days"]].fillna("Unavailable").to_numpy(),
        ))

    latest = plot_frame.iloc[-1]
    latest_name = _("legend_current") if latest_is_current else _("legend_latest_valid")
    fig.add_trace(go.Scatterpolar(
        theta=[latest["P"] * 15.0],
        r=[latest["D"]],
        mode="markers",
        marker=dict(color="#ffb703", size=15, line=dict(color="#1f2937", width=1.5), symbol="circle", opacity=0.95),
        name=latest_name,
        hovertemplate=common_hover,
        text=[latest["rhythm_day"].strftime("%Y-%m-%d")],
        customdata=latest[tooltip_cols].to_numpy().reshape(1, -1),
    ))

    fig.update_layout(
        title=dict(text=_("chart_polar_title"), x=0.02, xanchor="left", font=dict(color="#e5e7eb", size=18)),
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0, font=dict(size=10)),
        hovermode="closest",
        height=580,
        margin=dict(l=55, r=55, t=60, b=100),
        uirevision="constant",
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            angularaxis=dict(
                rotation=90,
                direction="clockwise",
                tickmode="array",
                tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
                ticktext=["0h", "+3h", "+6h", "+9h", "±12h", "-9h", "-6h", "-3h"],
                gridcolor="#4b5563",
                linecolor="#6b7280",
                tickfont=dict(color="#e5e7eb"),
            ),
            radialaxis=dict(
                autorange=True,
                rangemode="tozero",
                gridcolor="#374151",
                linecolor="#6b7280",
                tickfont=dict(color="#d1d5db"),
            ),
        ),
    )
    st.plotly_chart(fig, width="stretch")




def add_attractor_status_label(is_inside: bool):
    label = _("label_inside") if is_inside else _("label_outside")
    if is_inside:
        st.success(label)
    else:
        st.error(label)


def diagnose_attractor_state(p, d, p_limit, d_limit):
    if p is None or pd.isna(p) or d is None or pd.isna(d):
        return "diagnosis_insufficient", "#9ca3af"
    if abs(p) < p_limit and d < d_limit:
        return "diagnosis_locked", "#2a9d5b"
    if p >= p_limit and d >= d_limit:
        return "diagnosis_jetlag", "#d1495b"
    if p <= -p_limit and d >= d_limit:
        return "diagnosis_deprivation", "#d1495b"
    if p <= -p_limit and d < d_limit:
        return "diagnosis_advance", "#e9c46a"
    if p >= p_limit and d < d_limit:
        return "diagnosis_drift", "#e9c46a"
    return "diagnosis_unknown", "#9ca3af"


def build_rhythm_observation(p, d, h, p_limit, d_limit):
    if p is None or pd.isna(p) or d is None or pd.isna(d):
        return _("observation_insufficient")
    diagnosis_key, _diagnosis_color = diagnose_attractor_state(p, d, p_limit, d_limit)
    diagnosis_name = diagnosis_key.removeprefix("diagnosis_")
    return _(
        f"observation_{diagnosis_name}",
        p=f"{float(p):.2f}",
        d=f"{float(d):.2f}",
        h=f"{float(h):.3f}",
    )
def build_habit_observation(daily_points: pd.DataFrame, daily_summary: pd.DataFrame, target_wake: str):
    if daily_points.empty or daily_summary.empty:
        return {
            "wake": "N/A",
            "wake_state": _("habit_variable"),
            "lock": "0",
            "disturbances": "0",
            "trend": _("habit_stable"),
            "recovery": _("recovery_none"),
        }
    recent_points = daily_points.sort_values("rhythm_day").tail(7)
    wake_values = pd.to_datetime(recent_points["wake_time"], format="%H:%M", errors="coerce")
    wake_hours = wake_values.dt.hour + wake_values.dt.minute / 60.0
    target = datetime.strptime(target_wake, "%H:%M").hour + datetime.strptime(target_wake, "%H:%M").minute / 60.0
    deviations = ((wake_hours - target + 12.0) % 24.0) - 12.0
    valid_deviations = deviations.dropna()
    mean_deviation = float(valid_deviations.abs().mean()) if not valid_deviations.empty else None
    wake_state = _("habit_consistent") if mean_deviation is not None and mean_deviation <= 0.5 else _("habit_variable")
    wake_display = f"{mean_deviation:.1f}h" if mean_deviation is not None else "N/A"
    lock_streak = 0
    for is_inside in daily_summary.sort_values("rhythm_day")["in_attractor"].iloc[::-1]:
        if not bool(is_inside):
            break
        lock_streak += 1
    disturbance_count = int(
        daily_summary.sort_values("rhythm_day").tail(7)["disturbance"].fillna(0).astype(bool).sum()
    )
    recent_h = pd.to_numeric(daily_summary.sort_values("rhythm_day").tail(7)["H"], errors="coerce").dropna()
    if len(recent_h) < 2 or abs(float(recent_h.iloc[-1] - recent_h.iloc[0])) < 0.02:
        habit_trend = _("habit_stable")
    elif recent_h.iloc[-1] > recent_h.iloc[0]:
        habit_trend = _("habit_rising")
    else:
        habit_trend = _("habit_falling")
    return {
        "wake": wake_display,
        "wake_state": wake_state,
        "lock": str(lock_streak),
        "disturbances": str(disturbance_count),
        "trend": habit_trend,
        "recovery": build_recovery_observation(daily_summary),
    }


def build_recovery_observation(daily_summary: pd.DataFrame):
    if daily_summary.empty or "disturbance" not in daily_summary.columns:
        return _("recovery_none")
    disturbances = daily_summary[daily_summary["disturbance"].fillna(0).astype(bool)]
    if disturbances.empty:
        return _("recovery_none")
    latest_disturbance_day = disturbances["rhythm_day"].max()
    completed = daily_summary[
        daily_summary["recovery_days"].notna()
        & (daily_summary["rhythm_day"] >= latest_disturbance_day)
    ]
    if completed.empty:
        return _("recovery_pending")
    days = int(completed.iloc[-1]["recovery_days"])
    return _("recovery_completed", days=days)

def target_zone_distance(p, d, p_limit, d_limit):
    phase_excess = max(abs(float(p)) - p_limit, 0.0) / p_limit
    debt_excess = max(float(d) - d_limit, 0.0) / d_limit
    return math.hypot(phase_excess, debt_excess)


def check_convergence(summary_df, p_limit, d_limit):
    if len(summary_df) < 2:
        return "convergence_insufficient"
    ordered = summary_df.sort_values("rhythm_day")
    current = ordered.iloc[-1]
    previous = ordered.iloc[-2]
    if pd.isna(current["P"]) or pd.isna(current["D"]) or pd.isna(previous["P"]) or pd.isna(previous["D"]):
        return "convergence_insufficient"
    current_distance = target_zone_distance(current["P"], current["D"], p_limit, d_limit)
    previous_distance = target_zone_distance(previous["P"], previous["D"], p_limit, d_limit)
    if math.isclose(current_distance, previous_distance, abs_tol=1e-9):
        return "convergence_stable"
    if current_distance < previous_distance:
        return "converging"
    return "diverging"


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

    range_map = {
        "7D": 7,
        "30D": 30,
        "90D": 90,
    }
    days = range_map.get(range_label)
    if days is None:
        return filtered.sort_values("rhythm_day")
    start_date = latest_date - timedelta(days=days - 1)
    return filtered[(filtered["rhythm_day"].dt.date >= start_date) & (filtered["rhythm_day"].dt.date <= latest_date)].sort_values("rhythm_day")


def plot_core_trend_charts(daily_points: pd.DataFrame, range_label: str):
    filtered = filter_points_by_range(daily_points, range_label)
    if filtered.empty:
        st.info(_("info_no_trend_data"))
        return

    chart_frame = filtered.copy()
    chart_frame["rhythm_day"] = pd.to_datetime(chart_frame["rhythm_day"], errors="coerce")
    chart_frame = chart_frame.dropna(subset=["rhythm_day"])
    if chart_frame.empty:
        st.info(_("info_no_trend_dates"))
        return

    def clock_to_decimal(value):
        if not isinstance(value, str) or not validate_time_string(value):
            return pd.NA
        parsed = datetime.strptime(value, "%H:%M")
        return parsed.hour + parsed.minute / 60.0

    chart_frame["wake_clock_hour"] = chart_frame["wake_time"].apply(clock_to_decimal)
    chart_frame = chart_frame.sort_values("rhythm_day")

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08)

    fig.add_trace(go.Scatter(
        x=chart_frame["rhythm_day"], y=chart_frame["wake_clock_hour"],
        mode="lines+markers", marker=dict(color="#1d3557", size=6),
        line=dict(color="#1d3557", width=2),
        name=_("chart_wake"),
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            f"{_('chart_wake')}: %{{y:.1f}}<br>"
            "HH:MM: %{customdata}<extra></extra>"
        ),
        customdata=chart_frame["wake_time"],
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=chart_frame["rhythm_day"], y=chart_frame["D"],
        mode="lines+markers", marker=dict(color="#457b9d", size=6),
        line=dict(color="#457b9d", width=2),
        name=_("chart_sleep_debt"),
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            f"{_('chart_sleep_debt')}: %{{y:.2f}} h<extra></extra>"
        ),
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=chart_frame["rhythm_day"], y=chart_frame["H"],
        mode="lines+markers", marker=dict(color="#2a9d8f", size=6),
        line=dict(color="#2a9d8f", width=2),
        name=_("chart_habit"),
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            f"{_('chart_habit')}: %{{y:.3f}}<extra></extra>"
        ),
    ), row=3, col=1)

    fig.update_yaxes(title_text=_("chart_wake"), row=1, col=1)
    fig.update_yaxes(title_text=_("chart_sleep_debt"), row=2, col=1)
    fig.update_yaxes(title_text=_("chart_habit"), row=3, col=1)
    fig.update_xaxes(title_text=_("chart_date"), row=3, col=1)

    fig.update_layout(
        title=_("chart_title", range=range_label),
        showlegend=False,
        height=600,
        margin=dict(l=50, r=20, t=50, b=50),
    )
    st.plotly_chart(fig, width="stretch")



st.title(_("title"))
st.write(_("subtitle"))
st.caption(_("caption_naps"))


def initialize_test_parameter_state():
    if "test_target_wake" not in st.session_state:
        st.session_state.test_target_wake = datetime.strptime(config["target_wake"], "%H:%M").time()
    if "test_sleep_need_hours" not in st.session_state:
        st.session_state.test_sleep_need_hours = float(config["sleep_need_hours"])
    if "test_lambda_d" not in st.session_state:
        st.session_state.test_lambda_d = float(config["lambda_d"])
    if "test_alpha_up" not in st.session_state:
        st.session_state.test_alpha_up = float(config["alpha_up"])
    if "test_alpha_down" not in st.session_state:
        st.session_state.test_alpha_down = float(config["alpha_down"])
    if "test_recovery_k" not in st.session_state:
        st.session_state.test_recovery_k = float(config["recovery_k"])
    if "test_recovery_saturation_tau" not in st.session_state:
        st.session_state.test_recovery_saturation_tau = float(config["recovery_saturation_tau"])


initialize_test_parameter_state()


def get_active_parameters():
    attractor_settings = load_ui_settings()
    return {
        "target_wake": st.session_state.get("test_target_wake", datetime.strptime(config["target_wake"], "%H:%M").time()).strftime("%H:%M"),
        "sleep_need_hours": float(st.session_state.get("test_sleep_need_hours", config["sleep_need_hours"])),
        "lambda_d": float(st.session_state.get("test_lambda_d", config["lambda_d"])),
        "alpha_up": float(st.session_state.get("test_alpha_up", config["alpha_up"])),
        "alpha_down": float(st.session_state.get("test_alpha_down", config["alpha_down"])),
        "recovery_k": float(st.session_state.get("test_recovery_k", config["recovery_k"])),
        "recovery_saturation_tau": float(st.session_state.get("test_recovery_saturation_tau", config["recovery_saturation_tau"])),
        "attractor_p_limit": attractor_settings["attractor_p_limit"],
        "attractor_d_limit": attractor_settings["attractor_d_limit"],
        "target_utc_offset": attractor_settings["target_utc_offset"],
    }


ensure_profile_samples()
ui_settings = load_ui_settings()
profile_labels = {profile_id: _(f"profile_{profile_id}") for profile_id in PROFILE_IDS}

with st.sidebar:
    st.subheader("Language / 语言")
    lang_options = {"en": "English", "cn": "中文"}
    selected_lang = st.selectbox(
        "Language",
        options=list(lang_options.keys()),
        label_visibility="collapsed",
        format_func=lambda x: lang_options[x],
        index=0 if st.session_state.lang == "en" else 1,
        key="lang_selector",
    )
    if selected_lang != st.session_state.lang:
        st.session_state.lang = selected_lang
        st.rerun()

    st.subheader(_("profile_selector"))
    selected_profile_id = st.selectbox(
        _("profile_selector"),
        options=list(PROFILE_IDS),
        index=PROFILE_IDS.index(ui_settings["profile_id"]),
        format_func=profile_labels.__getitem__,
    )
    is_sample_profile = selected_profile_id in SAMPLE_PROFILE_IDS
    if is_sample_profile:
        st.caption(_("profile_read_only"))

    st.subheader(_("attractor_settings"))
    attractor_p_limit = st.number_input(
        _("attractor_p_limit"), min_value=0.1, max_value=12.0,
        value=ui_settings["attractor_p_limit"], step=0.1,
    )
    attractor_d_limit = st.number_input(
        _("attractor_d_limit"), min_value=0.1, max_value=24.0,
        value=ui_settings["attractor_d_limit"], step=0.1,
    )
    target_utc_offset = st.number_input(
        _("target_utc_offset"), min_value=-12.0, max_value=14.0,
        value=ui_settings["target_utc_offset"], step=0.25,
        help=_("target_utc_offset_help"),
    )
    st.caption(_("attractor_heuristic"))
    st.markdown("[{}](https://github.com/Hyperbolica-dev/MDRM)".format(_("copyright")))

if (
    attractor_p_limit != ui_settings["attractor_p_limit"]
    or attractor_d_limit != ui_settings["attractor_d_limit"]
    or target_utc_offset != ui_settings["target_utc_offset"]
    or selected_profile_id != ui_settings["profile_id"]
):
    save_ui_settings(attractor_p_limit, attractor_d_limit, target_utc_offset, selected_profile_id)

active_data_file = profile_data_path(selected_profile_id)
if not is_sample_profile:
    ensure_daily_backup(active_data_file)

active_params = get_active_parameters()
active_params["attractor_p_limit"] = attractor_p_limit
active_params["attractor_d_limit"] = attractor_d_limit
active_params["target_utc_offset"] = target_utc_offset
records_frame = load_records_frame(active_data_file)
daily_view, daily_summary, daily_points = get_daily_state_frames(records_frame, active_params)

st.subheader(_("dashboard_title"))
if daily_summary.empty:
    observer = {"P": 0.0, "D": 0.0, "H": 1.0, "in_attractor": 0, "rhythm_day": None}
else:
    observer = daily_summary.iloc[-1].to_dict()

biological_utc_offset = dynamics.estimate_biological_utc_offset(
    daily_summary["P"].tolist() if not daily_summary.empty else [],
    target_utc_offset,
)
dashboard_col1, dashboard_col2, dashboard_col3 = st.columns(3)
with dashboard_col1:
    p_val = observer.get("P")
    p_display = f"{p_val:.2f} h" if pd.notna(p_val) else "N/A"
    st.metric(_("metric_p"), p_display)
with dashboard_col2:
    st.metric(_("metric_d"), f"{float(observer.get('D', 0.0)):.2f} h")
with dashboard_col3:
    st.metric(_("metric_h"), f"{float(observer.get('H', 1.0)):.3f}")
dashboard_col4, dashboard_col5 = st.columns(2)
with dashboard_col4:
    status_label = _("label_inside") if int(observer.get("in_attractor", 0)) == 1 else _("label_outside")
    st.metric(_("metric_attractor"), status_label)
with dashboard_col5:
    st.metric(_("metric_biological_utc"), format_utc_offset(biological_utc_offset))

add_attractor_status_label(bool(observer.get("in_attractor", 0)))
st.subheader(_("observation_title"))
observation_p = observer.get("P") if not daily_summary.empty else None
st.info(
    build_rhythm_observation(
        observation_p,
        observer.get("D"),
        observer.get("H"),
        attractor_p_limit,
        attractor_d_limit,
    )
)
habit_observation = build_habit_observation(daily_points, daily_summary, active_params["target_wake"])
st.subheader(_("habit_observation_title"))
habit_col1, habit_col2, habit_col3, habit_col4 = st.columns(4)
with habit_col1:
    st.metric(_("habit_wake_consistency"), habit_observation["wake"], habit_observation["wake_state"])
with habit_col2:
    st.metric(_("habit_lock_streak"), habit_observation["lock"])
with habit_col3:
    st.metric(_("habit_disturbances"), habit_observation["disturbances"])
with habit_col4:
    st.metric(_("habit_trend"), habit_observation["trend"])
st.caption(f"{_('recovery_title')}: {habit_observation['recovery']}")

st.subheader(_("live_title"))
st.caption(_("live_caption"))
last_wake = daily_view["wake_end_dt"].max() if not daily_view.empty else None
target_local_time = (
    datetime.now(timezone.utc) + timedelta(hours=target_utc_offset)
).replace(tzinfo=None)
live_state = dynamics.calculate_live_state(
    last_wake,
    target_local_time,
    active_params["target_wake"],
    active_params["sleep_need_hours"],
    float(observer.get("D", 0.0)),
)
if live_state is None:
    st.info(_("live_no_data"))
else:
    live_col1, live_col2 = st.columns(2)
    with live_col1:
        st.metric(_("live_current_time"), live_state["current_time"].strftime("%Y-%m-%d %H:%M"))
    with live_col2:
        st.metric(_("live_awake"), f"{live_state['assumed_awake_hours']:.1f} h")
    live_col3, live_col4 = st.columns(2)
    with live_col3:
        st.metric(_("live_missed_sleep"), f"{live_state['missed_sleep_hours']:.1f} h")
    with live_col4:
        st.metric(_("live_projected_debt"), f"{live_state['projected_debt']:.1f} h")

if not daily_points.empty:
    latest_point = daily_points.sort_values("rhythm_day").iloc[-1]
    p_val = latest_point.get("P")
    wake_val = latest_point.get("wake_time")
    sleep_val = latest_point.get("sleep_hours")
    if pd.notna(p_val) and wake_val and sleep_val and sleep_val > 0:
        cbt_min = dynamics.estimate_cbt_min(str(wake_val), float(sleep_val))
        deadband = 0.5
        st.markdown("---")
        lc1, lc2 = st.columns(2)
        def _fmt(h):
            h24 = h + 24 if h < 0 else h
            hh = int(h24)
            mm = int(round((h24 - hh) * 60))
            if mm == 60:
                hh += 1
                mm = 0
            return f"{hh % 24:02d}:{mm:02d}"
        lc1.metric(_("cbt_min"), _fmt(cbt_min), help=_("cbt_min_help"))
        if not dynamics.can_recommend_light(p_val):
            lc2.warning(_("light_uncertain"))
            st.info(f"**{_('non_light_title')}**\n\n{_('non_light_guidance')}")
        elif abs(p_val) > deadband:
            scale = min(1.0, (abs(p_val) - deadband) / 2.0)
            offset = 3.0 * scale
            light_hour = cbt_min + offset if p_val > 0 else cbt_min - offset
            lc2.metric(_("light_window"), f"{_fmt(light_hour - 0.5)} - {_fmt(light_hour + 0.5)}", help=_("light_window_help"))
        else:
            lc2.success(_("light_deadband"))
    else:
        st.info(_("light_no_data"))
if daily_points.empty:
    st.info(_("info_no_records"))
else:
    st.caption(_("caption_trajectory"))
    trajectory_ranges = ["7D", "14D", "30D", "All"]
    selected_trajectory_range = st.radio(
        _("trajectory_range"),
        trajectory_ranges,
        index=1,
        horizontal=True,
    )
    trajectory_points = filter_phase_space_points(daily_points, selected_trajectory_range)
    render_phase_space_context(daily_points, attractor_p_limit, attractor_d_limit)
    use_polar = st.checkbox(_("polar_toggle"), value=DEFAULT_POLAR_VIEW)
    if use_polar:
        st.caption(_("caption_polar_trajectory"))
        draw_polar_state_trajectory(trajectory_points, attractor_p_limit, attractor_d_limit)
    else:
        draw_state_trajectory(trajectory_points, attractor_p_limit, attractor_d_limit)

    diag_label_key, diag_color = diagnose_attractor_state(
        observer.get("P"), observer.get("D"), attractor_p_limit, attractor_d_limit
    )
    conv_key = check_convergence(daily_summary, attractor_p_limit, attractor_d_limit)

    st.markdown("---")
    diag_col1, diag_col2 = st.columns(2)
    with diag_col1:
        st.markdown(
            f"<div style='color:#e0e0e0;padding:8px 12px;"
            f"border-left:4px solid {diag_color};"
            f"font-weight:600;font-size:1rem;'>{_(diag_label_key)}</div>",
            unsafe_allow_html=True,
        )
    with diag_col2:
        st.markdown(
            f"<div style='color:#e0e0e0;padding:8px 12px;"
            f"border-left:4px solid #8899aa;"
            f"font-weight:500;font-size:1rem;'>{_(conv_key)}</div>",
            unsafe_allow_html=True,
        )

    with st.expander(_("guide_title"), expanded=False):
        st.markdown(_("guide_content"))

st.subheader(_("charts_title"))
range_choice = st.selectbox(_("time_range"), ["7D", "30D", "90D", "All"], index=1)
plot_core_trend_charts(daily_points, range_choice)
latest_recommendation_point = daily_points.sort_values("rhythm_day").iloc[-1] if not daily_points.empty else None
recommendation_state = observer.copy()
if daily_summary.empty:
    recommendation_state["P"] = None
recommendation_cbt_min = None
if latest_recommendation_point is not None:
    recommendation_sleep = latest_recommendation_point.get("sleep_hours")
    recommendation_wake = latest_recommendation_point.get("wake_time")
    if recommendation_wake and pd.notna(recommendation_sleep) and float(recommendation_sleep) > 0:
        recommendation_cbt_min = dynamics.estimate_cbt_min(str(recommendation_wake), float(recommendation_sleep))
recommendation_candidates = build_recommendation_candidates(
    recommendation_state,
    active_params["target_wake"],
    active_params["sleep_need_hours"],
    rhythm_day=daily_summary.iloc[-1]["rhythm_day"] if not daily_summary.empty else date.today(),
    p_limit=attractor_p_limit,
    d_limit=attractor_d_limit,
    cbt_min=recommendation_cbt_min,
)
learning_interventions = empty_intervention_frame() if is_sample_profile else load_interventions()
with st.expander(_("empirical_title"), expanded=False):
    st.caption(_("empirical_caption"))
    empirical_report = build_empirical_status_report(daily_summary, daily_view, learning_interventions)
    validation_report = empirical_report["short_history"]
    action_report = empirical_report["action_coverage"]

    st.markdown(f"**{_('empirical_data_status')}**")
    data_col1, data_col2 = st.columns(2)
    data_col1.metric(_("empirical_transitions"), str(empirical_report["state_only"]["usable_transitions"]))
    data_col2.metric(_("empirical_interventions"), str(action_report["executed_interventions"]))
    action_types = ", ".join(action_report["action_types"]) if action_report["action_types"] else _("empirical_none")
    data_col3, data_col4 = st.columns(2)
    data_col3.metric(_("empirical_action_types"), action_types)
    validation_label = _("empirical_yes") if validation_report["chronological_validation_available"] else _("empirical_no")
    data_col4.metric(_("empirical_validation"), validation_label)

    st.markdown(f"**{_('empirical_model_status')}**")
    persistence_metrics = validation_report["persistence"]
    learned_metrics = validation_report["learned"]
    metric_rows = []
    for variable, metric_name in (("P", "P_circular_mae"), ("D", "D_mae"), ("H", "H_mae")):
        persistence_error = persistence_metrics.get(metric_name)
        learned_error = learned_metrics.get(metric_name)
        metric_rows.append({
            _("empirical_variable"): variable,
            _("empirical_persistence"): f"{persistence_error:.3f}" if pd.notna(persistence_error) else "N/A",
            _("empirical_learned"): f"{learned_error:.3f}" if pd.notna(learned_error) else "N/A",
            _("empirical_beats"): _("empirical_beats_yes") if validation_report["learned_beats_persistence"][variable] else _("empirical_beats_no"),
        })
    st.dataframe(pd.DataFrame(metric_rows), width="stretch", hide_index=True)

    st.markdown(f"**{_('empirical_forecast')}**")
    forecast = empirical_report["current_forecast"]
    if forecast["available"]:
        forecast_col1, forecast_col2 = st.columns(2)
        forecast_col1.metric(_("empirical_predicted_p"), f"{forecast['P_mean']:.2f} ± {forecast['P_std']:.2f} h")
        forecast_col2.metric(_("empirical_predicted_d"), f"{forecast['D_mean']:.2f} ± {forecast['D_std']:.2f} h")
        st.metric(_("empirical_predicted_h"), f"{forecast['H_mean']:.3f} ± {forecast['H_std']:.3f}")
        if not daily_summary.empty:
            latest_observed = daily_summary.iloc[-1]
            latest_phase = f"{latest_observed['P']:.2f}" if pd.notna(latest_observed["P"]) else "N/A"
            st.caption(_(
                "empirical_current_state",
                p=latest_phase,
                d=f"{latest_observed['D']:.2f}",
                h=f"{latest_observed['H']:.3f}",
            ))
        st.caption(_("empirical_forecast_caption"))
    else:
        st.info(_("empirical_forecast_unavailable", reason=forecast["reason"]))

    st.markdown(f"**{_('empirical_stage')}**")
    stage_key = f"empirical_stage_{empirical_report['system_stage']}"
    st.warning(_(stage_key))
    if not empirical_report["controller_eligible"]:
        st.warning(_("empirical_action_warning"))
    st.markdown(f"**{_('empirical_candidates')}**")
    st.info(_("empirical_candidates_hidden"))

    if not is_sample_profile:
        st.markdown("---")
        st.markdown(f"**{_('recommendation_title')}**")
        st.caption(_("recommendation_caption"))
        recommendation_labels = [
            f"{candidate['action_type']} · {candidate.get('recommended_time') or 'N/A'}"
            for candidate in recommendation_candidates
        ]
        selected_candidate_index = st.selectbox(
            _("recommendation_title"),
            options=range(len(recommendation_candidates)),
            format_func=lambda index: recommendation_labels[index],
        )
        selected_candidate = recommendation_candidates[selected_candidate_index]
        st.caption(_(selected_candidate["reason_key"]))
        st.markdown(f"**{_('empirical_log_title')}**")
        st.caption(_("empirical_log_caption"))
        candidate_day = pd.Timestamp(selected_candidate["rhythm_day"]).date()
        candidate_actual_time = datetime.strptime(
            selected_candidate["recommended_time"] or active_params["target_wake"],
            "%H:%M",
        ).time()
        candidate_duration = selected_candidate["recommended_duration_minutes"]
        candidate_duration_text = "" if candidate_duration in ("", None) else str(int(candidate_duration))
        with st.form("executed_intervention_form"):
            action_type_input = st.text_input(_("empirical_action_type"), value=selected_candidate["action_type"])
            action_day_input = st.date_input(_("empirical_action_day"), value=candidate_day)
            actual_time_input = st.time_input(_("empirical_actual_time"), value=candidate_actual_time)
            duration_input = st.text_input(_("empirical_duration"), value=candidate_duration_text)
            notes_input = st.text_input(_("empirical_notes"), value=selected_candidate["notes"])
            save_action = st.form_submit_button(_("empirical_save_action"))
        if save_action:
            try:
                append_intervention({
                    "rhythm_day": action_day_input.strftime("%Y-%m-%d"),
                    "action_type": action_type_input,
                    "recommended_time": selected_candidate["recommended_time"],
                    "planned_time": "",
                    "actual_time": actual_time_input.strftime("%H:%M"),
                    "duration_minutes": duration_input.strip(),
                    "executed": True,
                    "source": "user_report",
                    "notes": notes_input,
                })
                build_empirical_status_report.clear()
                st.success(_("empirical_action_saved"))
            except (OSError, TypeError, ValueError) as error:
                st.error(_("empirical_action_error", error=error))


with st.expander(_("test_panel_title"), expanded=False):
    st.caption(_("test_panel_caption"))
    test_col1, test_col2 = st.columns(2)
    with test_col1:
        st.session_state.test_target_wake = st.time_input(_("test_target_wake"), value=st.session_state.test_target_wake)
        st.session_state.test_sleep_need_hours = st.number_input(
            _("test_sleep_need"),
            min_value=0.0,
            max_value=24.0,
            value=float(st.session_state.test_sleep_need_hours),
            step=0.1,
        )
        st.session_state.test_recovery_k = st.number_input(
            _("test_recovery_k"),
            min_value=0.0,
            max_value=24.0,
            value=float(st.session_state.test_recovery_k),
            step=0.1,
        )
    with test_col2:
        st.session_state.test_lambda_d = st.number_input(
            _("test_lambda_d"),
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.test_lambda_d),
            step=0.01,
        )
        st.session_state.test_alpha_up = st.number_input(
            _("test_alpha_up"),
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.test_alpha_up),
            step=0.01,
        )
        st.session_state.test_alpha_down = st.number_input(
            _("test_alpha_down"),
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.test_alpha_down),
            step=0.01,
        )
        st.session_state.test_recovery_saturation_tau = st.number_input(
            _("test_recovery_saturation_tau"),
            min_value=0.1,
            max_value=12.0,
            value=float(st.session_state.test_recovery_saturation_tau),
            step=0.1,
        )

    if st.button(_("test_reset")):
        st.session_state.test_target_wake = datetime.strptime(config["target_wake"], "%H:%M").time()
        st.session_state.test_sleep_need_hours = float(config["sleep_need_hours"])
        st.session_state.test_lambda_d = float(config["lambda_d"])
        st.session_state.test_alpha_up = float(config["alpha_up"])
        st.session_state.test_alpha_down = float(config["alpha_down"])
        st.session_state.test_recovery_k = float(config["recovery_k"])
        st.session_state.test_recovery_saturation_tau = float(config["recovery_saturation_tau"])
        st.rerun()


active_params = get_active_parameters()

with st.form("daily_entry"):
    today = st.date_input(_("form_date"), date.today())
    col1, col2 = st.columns(2)
    with col1:
        sleep_time = st.text_input(_("form_sleep_time"), placeholder="HH:MM")
        wake_time = st.text_input(_("form_wake_time"), placeholder="HH:MM")
    with col2:
        momentum = st.slider(_("form_momentum"), 0, 10, 5)
        disturbance = st.checkbox(_("form_disturbance"), value=False)
        sleep_medication = st.checkbox(_("form_medication"), value=False)
    
    submitted = st.form_submit_button(_("form_submit"), disabled=is_sample_profile)

if submitted:
    if not TIME_PATTERN.match(sleep_time) or not TIME_PATTERN.match(wake_time):
        st.error("Time must be in HH:MM format")
        st.stop()

    df = load_records_frame(active_data_file)

    new_record = pd.DataFrame([{
        "schema_version": CURRENT_SCHEMA_VERSION,
        "date": today,
        "wake_time": wake_time,
        "sleep_time": sleep_time,
        "momentum": momentum,
        "disturbance": int(disturbance),
        "sleep_medication": bool(sleep_medication),
        "P": None,
        "D": None,
        "H": None,
        "in_attractor": None,
    }])

    df = pd.concat([df, new_record], ignore_index=True)

    summary, derived, daily_summary, persisted = rebuild_persisted_records(df, active_params)
    save_records_frame(persisted, create_backup=False, path=active_data_file)
    
    st.success(_("submit_success"))
    p_str = f"{summary['P']:.2f}" if pd.notna(summary.get('P')) else "N/A"
    st.write(
        _("submit_state",
          day=summary['rhythm_day'],
          p=p_str,
          d=summary['D'],
          h=summary['H'],
          sleep=summary['sleep_hours'],
          sessions=summary['session_count'])
    )

st.subheader(_("data_mgmt_title"))
st.caption(_("data_mgmt_caption"))

if records_frame.empty:
    st.info(_("info_no_data"))
else:
    if daily_view is not None and daily_summary is not None and not daily_summary.empty:
        state_by_day = daily_summary[["rhythm_day", "P", "D", "H", "in_attractor", "sleep_hours", "session_count"]]
        raw_preview = daily_view.merge(state_by_day, on="rhythm_day", how="left", suffixes=("", "_day"))
        st.dataframe(
            raw_preview[[
                "date",
                "wake_time",
                "sleep_time",
                "momentum",
                "disturbance",
                "sleep_medication",
                "rhythm_day",
                "sleep_hours",
                "session_count",
                "P_day",
                "D_day",
                "H_day",
                "in_attractor_day",
            ]],
            width="stretch",
            hide_index=True,
        )

    st.markdown("#### " + _("manual_mgmt"))
    editor_df = records_frame.copy()
    editor_df.insert(0, "_del", False)
    editor_df["date"] = pd.to_datetime(editor_df["date"], errors="coerce").dt.date
    editor_df["disturbance"] = editor_df["disturbance"].fillna(False).astype(bool)
    editor_df["sleep_medication"] = editor_df["sleep_medication"].fillna(False).astype(bool)

    edited_df = st.data_editor(
        editor_df,
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        disabled=True if is_sample_profile else ["schema_version", "P", "D", "H", "in_attractor"],
        column_config={
            "_del": st.column_config.CheckboxColumn(_("del_col"), help=_("del_help")),
            "date": st.column_config.DateColumn("date"),
            "wake_time": st.column_config.TextColumn("wake_time"),
            "sleep_time": st.column_config.TextColumn("sleep_time"),
            "momentum": st.column_config.NumberColumn("momentum", min_value=0, max_value=10, step=1),
            "disturbance": st.column_config.CheckboxColumn("disturbance", help=_("dist_help")),
            "sleep_medication": st.column_config.CheckboxColumn("sleep_medication", help=_("med_help")),
        },
    )

    if st.button(_("save_button"), type="primary", disabled=is_sample_profile):
        try:
            cleaned_df = edited_df.loc[~edited_df["_del"].fillna(False)].copy()
            cleaned_df = cleaned_df[["schema_version"] + RAW_COLUMNS]
            summary, derived, daily_summary, persisted = rebuild_persisted_records(cleaned_df, active_params)
            save_records_frame(persisted, create_backup=True, path=active_data_file)
            p_str = f"{summary['P']:.2f}" if pd.notna(summary.get('P')) else "N/A"
            st.success(
                _("save_ok",
                  day=summary['rhythm_day'],
                  p=p_str,
                  d=summary['D'],
                  h=summary['H'])
            )
            st.rerun()
        except Exception as exc:
            st.error(_("save_fail", exc=exc))

with st.expander(_("import_title"), expanded=False):
    st.caption(_("import_caption"))
    uploaded_file = st.file_uploader(_("import_uploader"), type=["csv"], accept_multiple_files=False)
    if uploaded_file is not None:
        try:
            imported_df = pd.read_csv(uploaded_file)
            validated_import = validate_import_frame(imported_df)
            if st.button(_("import_button"), type="primary", disabled=is_sample_profile):
                _, _, _, persisted = rebuild_persisted_records(validated_import, active_params)
                save_records_frame(persisted, create_backup=True, path=active_data_file)
                st.success(_("import_success"))
                st.rerun()
        except Exception as exc:
            st.error(_("import_fail", exc=exc))
