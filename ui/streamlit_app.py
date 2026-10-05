import streamlit as st
import pandas as pd
import yaml
import os
import importlib
import re
import math
import hashlib
import numpy as np
from datetime import date, datetime, timedelta, timezone
import sys

import plotly.graph_objects as go

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from model import dynamics, sleep_pressure, phase_observation, recommendations, phase_objective
phase_observation = importlib.reload(phase_observation)
phase_objective = importlib.reload(phase_objective)
recommendations = importlib.reload(recommendations)
sleep_pressure = importlib.reload(sleep_pressure)
from model.interventions import append_intervention, empty_intervention_frame, load_interventions
from model.jev_decision import build_jev_payload, evaluate_jev
from ui.medication_journal import render_medication_journal
from model.record_storage import atomic_write_csv, create_record_backup, ensure_daily_record_backup
from ui import phase_space
phase_space = importlib.reload(phase_space)
from ui.phase_space import DEFAULT_POLAR_VIEW, daily_target_mask, filter_phase_space_points, latest_plottable_is_current, build_phase_line_frame, phase_step_is_contiguous
from ui import phase_space_3d
phase_space_3d = importlib.reload(phase_space_3d)
from ui.phase_space_3d import build_phase_space_3d_figure
from ui.core_charts import build_core_trend_figure
from ui import routine_patterns
routine_patterns = importlib.reload(routine_patterns)
from ui.routine_patterns import render_routine_patterns
from ui import record_calendar
record_calendar = importlib.reload(record_calendar)
from ui.record_calendar import build_date_input_calendar_css, classify_entry_dates
from ui import entry_calendar, daily_overview
entry_calendar = importlib.reload(entry_calendar)
daily_overview = importlib.reload(daily_overview)
from ui.entry_calendar import render_entry_calendar
from ui.daily_overview import render_daily_overview
from ui import sleep_pressure as pressure_ui
pressure_ui = importlib.reload(pressure_ui)
from ui import phase_objective as objective_ui
objective_ui = importlib.reload(objective_ui)
from model.recommendations import build_recommendation_candidates
from model.time_input import is_clock_time, normalize_clock_time
from model.sleep_entry import parse_sleep_intervals, validate_sleep_windows
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
        "err_time_format": "{column} column contains an invalid time. Use examples like 08:30, 830, or ８：３０.",
        "err_time_entry": "Please enter valid times. Examples: 08:30, 830, 8:3, or ８：３０.",
        "err_duplicate_record": "This exact sleep record already exists. Nothing was added.",
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
        "today_title": "Today",
        "today_log_title": "Confirm last sleep",
        "today_log_caption": "Record the last sleep first. Normal entry should take about ten seconds.",
        "today_state_title": "Current direction",
        "today_state_empty": "Record the latest sleep to establish the current direction.",
        "today_state_phase_unknown": "Wake regularity is {routine}, but the current phase direction is not yet reliable.",
        "today_state_summary": "Wake timing is {routine}; the rhythm is {phase}; sleep debt is {debt}.",
        "today_routine_stable": "relatively consistent in the recorded window",
        "today_routine_variable": "still variable",
        "today_routine_unknown": "not established yet",
        "today_phase_target": "near the target",
        "today_phase_late": "about {hours} hours later than the target",
        "today_phase_early": "about {hours} hours earlier than the target",
        "today_debt_high": "elevated",
        "today_debt_controlled": "currently controlled",
        "today_action_title": "Today's primary action",
        "today_action_when": "Suggested time",
        "today_action_duration": "Suggested duration",
        "today_action_reason": "Why this action",
        "today_alternatives_hint": "All generated alternatives remain available in the analysis section below.",
        "analysis_title": "Analysis and research details",
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
        "label_unknown": "Not established",
        "info_no_records": "No records yet. Use the daily entry form below to start the observer.",
        "caption_trajectory": "Green = one-day target zone; formal lock requires 7 consecutive qualifying days. Gray→blue = older→newer; gold = latest plottable state. Lines break at missing phases/dates and at the Cartesian ±12h seam. The arrow appears only for the latest continuous step.",
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
        "form_time_help": "Accepts 08:30, 830, 8:3, 8pm, 8点半, and full-width forms such as ８：３０. Values are normalized to HH:MM when submitted.",
        "form_momentum": "Momentum (O3) [0-dysregulated – 10-ideal]",
        "form_disturbance": "Major disturbance (O4) (e.g. all-nighter / illness)",
        "form_medication": "Sleep-aid medication disturbance",
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
        "med_help": "Mark sleep-aid use associated with this sleep. Names, doses and times are not required; this does not establish a medication effect.",
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
        "chart_routine_stability": "Routine Stability (shadow)",
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
        "observation_locked": "The latest recorded P={p}h and modeled D={d}h qualify under the selected thresholds. Formal lock still depends on the consecutive-day streak.",
        "observation_jetlag": "Sleep midpoint is later than target (P={p}h); modeled debt D={d}h is above the selected threshold.",
        "observation_deprivation": "Sleep midpoint is earlier than target (P={p}h); modeled debt D={d}h is above the selected threshold.",
        "observation_advance": "Sleep midpoint is earlier than target (P={p}h); modeled debt D={d}h is below the selected threshold.",
        "observation_drift": "Sleep midpoint is later than target (P={p}h); modeled debt D={d}h is below the selected threshold.",
        "observation_unknown": "The current pattern is mixed: keep wake time stable and collect more consecutive records before changing intervention timing.",
        "habit_observation_title": "Habit observation",
        "habit_routine_stability": "Routine stability (shadow)",
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
        "phase_3d_title": "3D Time View [Experimental]",
        "phase_3d_caption": "X = target offset P, Y = modeled debt D, Z = days from the latest record. Start oblique; use fixed orthographic views to compare each pair. Gold marks the latest plottable date; gray→blue means older→newer.",
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
        "empirical_action_warning": "Action effects are not yet identifiable. Rule-based candidates remain visible, but the learned model cannot compare their effects yet.",
        "recommendation_title": "Recommendation draft",
        "recommendation_caption": "This deterministic draft is not an execution record. Review or edit it, then submit explicitly if you carried it out.",
        "recommendation_reason_data": "Data is insufficient; use a conservative stabilization action while collecting records.",
        "recommendation_reason_phase_uncertain": "Phase is outside the safe light range; use stabilization without intentional phase-shifting light.",
        "recommendation_reason_debt": "Sleep debt is above the selected limit; prioritize recovery before phase shifting.",
        "recommendation_reason_phase": "Current phase displacement is within the safe range; the candidate follows the CBT_min light window.",
        "recommendation_reason_maintain": "Phase is inside the deadband; maintain the wake anchor instead of adding phase-shifting light.",
        "recommendation_reason_execution": "Draft recommendation; only explicit submission records execution.",
        "jev_shadow_title": "Jev shadow review",
        "jev_shadow_caption": "Optional observe-only review of existing candidates. It cannot create actions, override local safety gates, or record execution.",
        "jev_shadow_run": "Run Jev shadow review",
        "jev_shadow_disabled": "Jev is not configured. Set TYPESAFE_API_KEY in the process environment to enable it.",
        "jev_shadow_unavailable": "Jev is unavailable; the local deterministic recommendation remains unchanged.",
        "jev_shadow_invalid": "Jev returned an invalid decision; the local deterministic recommendation remains unchanged.",
        "jev_shadow_preference": "Jev's shadow opinion: consider {candidate} first",
        "jev_shadow_single": "Jev's shadow opinion: {candidate} remains reasonable to consider",
        "jev_shadow_meaning": "This is a second opinion over existing candidates. It does not change the MRDM recommendation or execute anything.",
        "jev_assurance": "Overall assurance",
        "jev_level_high": "Relatively strong",
        "jev_level_medium": "Moderate",
        "jev_level_low": "Limited",
        "jev_single_note": "Only one local candidate was supplied, so Jev did not make a meaningful comparison between alternatives.",
        "jev_technical_title": "Technical probabilities",
        "jev_metric_confidence": "Choice clarity",
        "jev_metric_safety": "Local-rule compatibility",
        "jev_metric_evidence": "Evidence sufficiency",
        "jev_help_confidence": "How clearly Jev separates this candidate from the alternatives. It is not the probability that the advice is correct.",
        "jev_help_safety": "Whether Jev sees a conflict with the supplied local gates. This is not a clinical safety probability; MRDM's local rules remain authoritative.",
        "jev_help_evidence": "Whether the coarse information sent to Jev appears sufficient for this comparison.",
        "jev_low_evidence": "Jev considers the available evidence limited. Treat this result as a weak prompt for review, not a decision.",
        "jev_shared_title": "What is sent to Jev?",
        "jev_shared_caption": "Only the following coarse buckets and candidate fields are sent. Dates, profiles, notes, exact values, medication details, and history are excluded.",
        "jev_shared_state": "Coarse current state",
        "jev_shared_candidates": "Candidate summary",
        "candidate_action": "Action",
        "candidate_time": "Suggested time",
        "candidate_duration": "Duration",
        "candidate_basis": "Basis",
        "candidate_rule_basis": "Local MRDM rule",
        "action_light": "Timed bright light",
        "action_sleep_recovery": "Protected sleep recovery",
        "action_stabilize_wake": "Stabilize wake time",
        "action_maintain_wake": "Maintain wake anchor",
        "jev_shadow_vetoed": "All candidates were vetoed locally; Jev was not called.",
        "empirical_candidates": "5. Candidate actions",
        "empirical_candidates_hidden": "Candidates are always shown. System-identification status only controls whether the learned model may compare predicted action effects.",
        "empirical_log_title": "Action feedback",
        "empirical_log_caption": "Report what happened. A displayed or accepted suggestion is never treated as executed.",
        "empirical_action_type": "Action type",
        "empirical_action_day": "Rhythm day",
        "empirical_actual_time": "Actual time",
        "empirical_response": "What happened?",
        "response_completed": "Completed",
        "response_partial": "Partly completed",
        "response_accepted": "Accepted / planned",
        "response_deferred": "Do later",
        "response_not_completed": "Not completed",
        "response_declined": "Declined",
        "response_not_seen": "I did not see this in time",
        "empirical_duration": "Duration minutes (optional)",
        "empirical_notes": "Notes (optional)",
        "empirical_save_action": "Save action feedback",
        "empirical_action_saved": "Action feedback saved.",
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
        "err_time_format": "{column} 列包含无效时间。可输入 08:30、830 或 ８：３０ 等格式。",
        "err_time_entry": "请输入有效时间，例如 08:30、830、8:3 或 ８：３０。",
        "err_duplicate_record": "这条完全相同的睡眠记录已存在，未重复添加。",
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
        "today_title": "今天",
        "today_log_title": "确认昨夜睡眠",
        "today_log_caption": "先记录最近一次睡眠；正常情况下约十秒即可完成。",
        "today_state_title": "当前方向",
        "today_state_empty": "记录最近一次睡眠后，系统才能建立当前方向。",
        "today_state_phase_unknown": "起床规律度{routine}，但当前相位方向还不可靠。",
        "today_state_summary": "起床时间{routine}；整体节律{phase}；睡眠债{debt}。",
        "today_routine_stable": "在记录窗口内较一致",
        "today_routine_variable": "仍有明显波动",
        "today_routine_unknown": "尚未建立",
        "today_phase_target": "已接近目标",
        "today_phase_late": "比目标晚约 {hours} 小时",
        "today_phase_early": "比目标早约 {hours} 小时",
        "today_debt_high": "偏高",
        "today_debt_controlled": "目前受控",
        "today_action_title": "今日主行动",
        "today_action_when": "建议时间",
        "today_action_duration": "建议持续",
        "today_action_reason": "为什么是它",
        "today_alternatives_hint": "全部已生成备选仍会显示在下方分析区域中。",
        "analysis_title": "分析与研究详情",
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
        "label_unknown": "尚未建立",
        "info_no_records": "尚无记录，请使用下方每日录入表单启动观察器。",
        "caption_trajectory": "绿色 = 单日达标区，正式锁定需连续 7 天达标。灰→蓝 = 旧→新，金色 = 最近可绘制状态。缺失日期、无效相位和直角图 ±12 小时接缝处断线；仅在最新一步连续有效时显示箭头。",
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
        "form_time_help": "支持 08:30、830、8:3、8点半，以及 ８：３０ 等全角写法；提交后会统一整理为 HH:MM。",
        "form_momentum": "动量 (O3) [0-失调 – 10-理想]",
        "form_disturbance": "重大扰动 (O4)（如通宵/疾病）",
        "form_medication": "助眠药物扰动",
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
        "med_help": "本次睡眠有助眠药物介入时勾选。不必填写药名、剂量或时间；标记不代表已确认药物造成移相。",
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
        "chart_routine_stability": "作息稳定性（影子指标）",
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
        "observation_locked": "最新记录的 P={p}h、模型 D={d}h 达到所选阈值；正式锁定仍取决于连续达标日数。",
        "observation_jetlag": "睡眠中点晚于目标（P={p}h），模型睡眠债 D={d}h 高于所选阈值。",
        "observation_deprivation": "睡眠中点早于目标（P={p}h），模型睡眠债 D={d}h 高于所选阈值。",
        "observation_advance": "睡眠中点早于目标（P={p}h），模型睡眠债 D={d}h 低于所选阈值。",
        "observation_drift": "睡眠中点晚于目标（P={p}h），模型睡眠债 D={d}h 低于所选阈值。",
        "observation_unknown": "当前模式较混合：保持起床时间稳定，连续记录更多数据后再改变干预时点。",
        "habit_observation_title": "习惯观察",
        "habit_routine_stability": "作息稳定性（影子指标）",
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
        "phase_3d_title": "3D 时间视图【实验】",
        "phase_3d_caption": "X = P 目标偏移，Y = D 模型睡眠债，Z = 距最新记录的天数。默认斜视；固定正交视角便于比较两轴。金点标注最近可绘制日期，灰→蓝表示旧→新。",
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
        "empirical_action_warning": "行动效应尚不可识别。规则候选仍会显示，但学习模型暂时不能比较它们的效果。",
        "recommendation_title": "推荐草稿",
        "recommendation_caption": "这是确定性推荐草稿，不是执行记录。请审核或修改，只有明确提交后才会记录实际执行。",
        "recommendation_reason_data": "数据不足：继续收集记录期间，先执行保守的节律稳定行动。",
        "recommendation_reason_phase_uncertain": "相位超出安全光疗范围：采用稳定化行动，不进行主动移相强光照射。",
        "recommendation_reason_debt": "睡眠债超过当前阈值：先恢复睡眠，再进行相位调整。",
        "recommendation_reason_phase": "当前相位偏移处于安全范围：候选时间依据 CBT_min 光疗窗口生成。",
        "recommendation_reason_maintain": "相位处于死区：保持起床锚点，不增加主动移相光疗。",
        "recommendation_reason_execution": "推荐草稿；只有明确提交才会记录实际执行。",
        "jev_shadow_title": "Jev 影子评审",
        "jev_shadow_caption": "仅对已有候选进行可选的观察性评审；不能生成行动、覆盖本地安全门或记录执行。",
        "jev_shadow_run": "运行 Jev 影子评审",
        "jev_shadow_disabled": "Jev 尚未配置。请在进程环境中设置 TYPESAFE_API_KEY 后启用。",
        "jev_shadow_unavailable": "Jev 当前不可用；本地确定性建议保持不变。",
        "jev_shadow_invalid": "Jev 返回了无效决策；本地确定性建议保持不变。",
        "jev_shadow_preference": "Jev 的影子意见：优先考虑「{candidate}」",
        "jev_shadow_single": "Jev 的影子意见：「{candidate}」可以继续作为考虑项",
        "jev_shadow_meaning": "这是对已有候选的第二意见，不会改变 MRDM 建议，也不会自动执行。",
        "jev_assurance": "综合把握",
        "jev_level_high": "相对较强",
        "jev_level_medium": "中等",
        "jev_level_low": "有限",
        "jev_single_note": "本次只有一个本地候选，因此 Jev 没有进行有意义的候选间比较。",
        "jev_technical_title": "技术概率",
        "jev_metric_confidence": "选择清晰度",
        "jev_metric_safety": "本地规则兼容度",
        "jev_metric_evidence": "证据充分度",
        "jev_help_confidence": "Jev 区分该候选与其他候选的清晰程度，不是“建议正确率”。",
        "jev_help_safety": "Jev 是否发现候选与本地门控冲突；这不是临床安全概率，MRDM 本地规则始终优先。",
        "jev_help_evidence": "Jev 判断当前发送的信息是否足以支持这次比较。",
        "jev_low_evidence": "Jev 认为现有证据有限。请把结果视为提醒复核，而不是决策。",
        "jev_shared_title": "后台向 Jev 发送了什么？",
        "jev_shared_caption": "只发送下面列出的粗粒度区间和候选字段；不发送日期、用户、备注、精确数值、药物详情或历史记录。",
        "jev_shared_state": "粗粒度当前状态",
        "jev_shared_candidates": "候选摘要",
        "candidate_action": "行动",
        "candidate_time": "建议时间",
        "candidate_duration": "持续时间",
        "candidate_basis": "依据",
        "candidate_rule_basis": "MRDM 本地规则",
        "action_light": "定时强光",
        "action_sleep_recovery": "优先恢复睡眠",
        "action_stabilize_wake": "稳定起床时间",
        "action_maintain_wake": "保持起床锚点",
        "jev_shadow_vetoed": "所有候选均被本地规则否决；未调用 Jev。",
        "empirical_candidates": "5. 候选行动",
        "empirical_candidates_hidden": "候选始终显示。系统识别状态只决定学习模型能否比较行动效果。",
        "empirical_log_title": "行动反馈",
        "empirical_log_caption": "请记录实际发生的情况。建议被显示或接受，都不等于已执行。",
        "empirical_action_type": "行动类型",
        "empirical_action_day": "节律日",
        "empirical_actual_time": "实际时间",
        "empirical_response": "实际发生了什么？",
        "response_completed": "已完成",
        "response_partial": "部分完成",
        "response_accepted": "已接受／已计划",
        "response_deferred": "稍后再做",
        "response_not_completed": "未完成",
        "response_declined": "不采用",
        "response_not_seen": "当时没看到这条建议",
        "empirical_duration": "持续分钟数（可选）",
        "empirical_notes": "备注（可选）",
        "empirical_save_action": "保存行动反馈",
        "empirical_action_saved": "已保存行动反馈。",
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
CURRENT_SCHEMA_VERSION = 2
ATTRACTOR_DAYS = 7
BACKUP_RETENTION_COUNT = 30
LEGACY_RAW_COLUMNS = ["date", "wake_time", "sleep_time", "momentum", "disturbance", "sleep_medication"]
RAW_COLUMNS = LEGACY_RAW_COLUMNS + ["awake_minutes", "awake_unknown"]
META_COLUMNS = ["schema_version"]
DERIVED_COLUMNS = ["P", "D", "H", "in_attractor"]
PREFERRED_COLUMNS = META_COLUMNS + RAW_COLUMNS + DERIVED_COLUMNS
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

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
        "lang": "en",
        "target_wake": config["target_wake"],
        "sleep_need_hours": float(config["sleep_need_hours"]),
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
            "lang": loaded.get("lang") if loaded.get("lang") in {"en", "cn"} else "en",
            "target_wake": datetime.strptime(loaded.get("target_wake", defaults["target_wake"]), "%H:%M").strftime("%H:%M"),
            "sleep_need_hours": min(16.0, max(1.0, float(loaded.get("sleep_need_hours", defaults["sleep_need_hours"])))),
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
                "lang": st.session_state.lang,
                "target_wake": st.session_state.get("test_target_wake", datetime.strptime(config["target_wake"], "%H:%M").time()).strftime("%H:%M"),
                "sleep_need_hours": float(st.session_state.get("test_sleep_need_hours", config["sleep_need_hours"])),
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
    normalized["schema_version"] = CURRENT_SCHEMA_VERSION
    for column, default in {"awake_minutes": 0, "awake_unknown": False}.items():
        if column not in normalized:
            normalized[column] = default
        normalized[column] = normalized[column].fillna(default)
    return normalized


def ensure_daily_backup(data_file: str = DATA_FILE):
    return ensure_daily_record_backup(data_file, BACKUP_DIR, retention_count=BACKUP_RETENTION_COUNT)


def validate_date_string(value: str) -> bool:
    return bool(DATE_PATTERN.match(str(value)))


def validate_time_string(value: str) -> bool:
    return is_clock_time(value)


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
        if version_values[0] not in (1, CURRENT_SCHEMA_VERSION):
            raise ValueError(_("err_version_unsupported", v=version_values[0], current=CURRENT_SCHEMA_VERSION))
    else:
        working["schema_version"] = CURRENT_SCHEMA_VERSION

    working = ensure_schema_version_column(working)
    missing_columns = [column for column in LEGACY_RAW_COLUMNS if column not in working.columns]
    if missing_columns:
        raise ValueError(_("err_missing_columns", cols=", ".join(missing_columns)))

    required_values = working[RAW_COLUMNS].copy()
    if required_values.isna().any().any():
        raise ValueError(_("err_empty_values"))

    invalid_dates = [value for value in required_values["date"].astype(str).tolist() if not validate_date_string(value)]
    if invalid_dates:
        raise ValueError(_("err_date_format"))

    for column in ["wake_time", "sleep_time"]:
        normalized_times = required_values[column].map(normalize_clock_time)
        if normalized_times.isna().any():
            raise ValueError(_("err_time_format", column=column))
        required_values[column] = normalized_times

    normalized = normalize_raw_records(working[RAW_COLUMNS])
    normalized = ensure_schema_version_column(normalized)
    return normalized


def write_records_frame(df: pd.DataFrame, path: str = DATA_FILE):
    output = ensure_schema_version_column(df.copy())
    for column in PREFERRED_COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA
    output = output[PREFERRED_COLUMNS]
    atomic_write_csv(output, path, index=False)


def load_records_frame(path: str = DATA_FILE):
    if not os.path.exists(path):
        return get_empty_records_frame()

    df = pd.read_csv(path)
    df = ensure_schema_version_column(df)
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
    normalized = ensure_schema_version_column(df.copy())

    if normalized.empty:
        return pd.DataFrame(columns=RAW_COLUMNS)

    for column in RAW_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = pd.NA

    normalized = normalized[RAW_COLUMNS].copy()
    normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce").dt.date
    normalized["wake_time"] = normalized["wake_time"].map(normalize_clock_time)
    normalized["sleep_time"] = normalized["sleep_time"].map(normalize_clock_time)
    normalized["momentum"] = pd.to_numeric(normalized["momentum"], errors="coerce")
    normalized["disturbance"] = pd.to_numeric(normalized["disturbance"], errors="coerce")
    normalized["sleep_medication"] = normalized["sleep_medication"].fillna(False).astype(bool)
    normalized["awake_minutes"] = pd.to_numeric(normalized["awake_minutes"], errors="coerce")
    normalized["awake_unknown"] = normalized["awake_unknown"].map(lambda value: str(value).lower() in {"true", "1"})
    if normalized["awake_minutes"].isna().any():
        raise ValueError("Invalid awake minutes")

    if normalized[["date", "wake_time", "sleep_time", "disturbance"]].isna().any().any() or (normalized["momentum"].isna() & normalized["sleep_time"].ne(normalized["wake_time"])).any():
        raise ValueError(_("err_raw_invalid"))

    normalized["date"] = normalized["date"].astype(str)
    normalized["momentum"] = normalized["momentum"].astype("Int64")
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
        params["routine_wake_tau_hours"],
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
        params["routine_wake_tau_hours"],
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
    if os.path.exists(path):
        stored_versions = pd.read_csv(path, usecols=lambda name: name == "schema_version")
        create_backup = create_backup or (not stored_versions.empty and bool((pd.to_numeric(stored_versions.get("schema_version"), errors="coerce") != CURRENT_SCHEMA_VERSION).any()))
    if create_backup and os.path.exists(path):
        create_record_backup(path, BACKUP_DIR, retention_count=BACKUP_RETENTION_COUNT)

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
        params["routine_wake_tau_hours"],
    )

    if daily_summary.empty:
        return daily_view, daily_summary, pd.DataFrame()

    pressure_frame = sleep_pressure.build_sleep_pressure_frame(daily_view, daily_summary)
    daily_summary = daily_summary.merge(pressure_frame, on="rhythm_day", how="left")
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
        for column in ["P", "D", "H", "routine_stability", "in_attractor", "disturbance", "recovery_days", "sleep_hours", "session_count", "observation_status", "sleep_duration_known", "state_estimated", "S", "S_low", "S_high", "pressure_at"]:
            point_row[column] = summary_lookup.loc[rhythm_day, column]
        daily_points_rows.append(point_row)

    daily_points = pd.DataFrame(daily_points_rows).sort_values("rhythm_day")
    return daily_view, daily_summary, daily_points
def recommendation_context_key(profile_id, current_state, candidate, context_generation=0):
    state_values = []
    for name in ("P", "D", "H"):
        value = current_state.get(name)
        state_values.append("na" if value is None or pd.isna(value) else str(value))
    candidate_values = [
        profile_id,
        str(context_generation),
        str(pd.Timestamp(candidate["rhythm_day"]).date()),
        str(candidate["action_type"]),
        str(candidate.get("recommended_time") or ""),
        str(candidate.get("recommended_duration_minutes") or ""),
        str(candidate.get("reason_key") or ""),
        *state_values,
    ]
    return "recommendation:" + ":".join(candidate_values)


def decision_id_for_context(context_key):
    return "decision:" + hashlib.sha256(context_key.encode("utf-8")).hexdigest()[:24]


def recommendation_selector_key(profile_id, current_state, candidates, context_generation=0):
    candidate_keys = [
        recommendation_context_key(profile_id, current_state, candidate, context_generation)
        for candidate in candidates
    ]
    return "recommendation_selector:" + "|".join(candidate_keys)


def initialize_recommendation_draft_state(state, context_key, candidate, target_wake):
    prefix = f"recommendation_draft:{context_key}"
    candidate_day = pd.Timestamp(candidate["rhythm_day"]).date()
    actual_time = candidate.get("recommended_time") or target_wake
    duration = candidate.get("recommended_duration_minutes")
    values = {
        "action_type": candidate["action_type"],
        "action_day": candidate_day,
        "actual_time": datetime.strptime(actual_time, "%H:%M").time(),
        "duration": "" if duration in ("", None) else str(int(duration)),
        "notes": candidate["notes"],
    }
    keys = {name: f"{prefix}:{name}" for name in values}
    for name, key in keys.items():
        if key not in state:
            state[key] = values[name]
    return keys


def localized_action_name(action_type):
    action_key = f"action_{action_type}"
    return _(action_key) if action_key in L[st.session_state.lang] else action_type


def normalize_daily_entry_times():
    for key in ("daily_sleep_time", "daily_wake_time"):
        normalized = normalize_clock_time(st.session_state.get(key))
        if normalized is not None:
            st.session_state[key] = normalized


def build_today_direction(daily_summary, observer, p_limit, d_limit):
    if daily_summary.empty:
        return _("today_state_empty")
    recent = daily_summary.sort_values("rhythm_day").tail(7)
    routine_values = pd.to_numeric(recent.get("routine_stability", pd.Series(dtype=float)), errors="coerce").dropna()
    if routine_values.empty:
        routine = _("today_routine_unknown")
    elif float(routine_values.mean()) >= 0.75:
        routine = _("today_routine_stable")
    else:
        routine = _("today_routine_variable")
    p_value = observer.get("P")
    if p_value is None or pd.isna(p_value):
        return _("today_state_phase_unknown", routine=routine)
    phase_value = float(p_value)
    if abs(phase_value) < float(p_limit):
        phase = _("today_phase_target")
    elif phase_value > 0:
        phase = _("today_phase_late", hours=f"{abs(phase_value):.1f}")
    else:
        phase = _("today_phase_early", hours=f"{abs(phase_value):.1f}")
    debt_value = observer.get("D")
    debt = _("today_debt_high") if debt_value is not None and pd.notna(debt_value) and float(debt_value) >= float(d_limit) else _("today_debt_controlled")
    return _("today_state_summary", routine=routine, phase=phase, debt=debt)

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
    next_day = None
    for index in range(len(ordered) - 1, -1, -1):
        is_qualifying = qualifying.iloc[index]
        current_day = ordered.iloc[index]["rhythm_day"]
        if not bool(is_qualifying):
            break
        if next_day is not None and next_day - current_day != pd.Timedelta(days=1):
            break
        streak += 1
        next_day = current_day
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
        if phase_step_is_contiguous(previous, latest, circular=True):
            context["phase_progress"] = abs(float(previous["P"])) - abs(float(latest["P"]))
            context["debt_progress"] = float(previous["D"]) - float(latest["D"])
    return context


def render_phase_space_context(daily_points: pd.DataFrame, p_limit: float, d_limit: float):
    context = build_phase_space_context(daily_points, p_limit, d_limit)
    if context is None:
        return
    chinese = st.session_state.lang != "en"
    record_day = context["current_day"].date()
    st.caption(f"记录截至 {record_day} · 相图反映该日的记录状态" if chinese else f"Records through {record_day} · The chart reflects that recorded day")
    age = (date.today() - record_day).days
    if age > 1:
        st.info(f"最新记录距今天 {age} 天，不能据此确认今天的作息状态。" if chinese else f"The latest record is {age} days old; today's routine is not established by this chart.")
    latest_point = daily_points.sort_values("rhythm_day").iloc[-1]
    if bool(latest_point.get("state_estimated", False)):
        st.warning("含未知睡眠时长：相图中的状态是估计值。" if chinese else "Unknown sleep duration in history: plotted states are estimates.")
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
            font=dict(size=11),
        )

    trajectory_line = build_phase_line_frame(plot_frame)
    fig.add_trace(go.Scatter(
        x=trajectory_line["P"],
        y=trajectory_line["D"],
        mode="lines",
        line=dict(color="#9ca3af", width=1.5),
        showlegend=False,
        hoverinfo="skip",
    ))
    tail = build_phase_line_frame(plot_frame[plot_frame["rhythm_day"] >= latest_day - pd.Timedelta(days=6)])
    fig.add_trace(go.Scatter(
        x=tail["P"],
        y=tail["D"],
        mode="lines",
        line=dict(color="#4b5563", width=2.5),
        showlegend=False,
        hoverinfo="skip",
    ))
    if n >= 2 and latest_is_current and phase_step_is_contiguous(plot_frame.iloc[-2], plot_frame.iloc[-1]):
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
            showarrow=False, yshift=14, font=dict(size=11),
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
        title=dict(text=_("chart_phase_title"), x=0.02, xanchor="left", font=dict(size=18)),
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
    trajectory_line = build_phase_line_frame(plot_frame, circular=True)
    fig.add_trace(go.Scatterpolar(
        theta=trajectory_line["P"] * 15.0,
        r=trajectory_line["D"],
        mode="lines",
        line=dict(color="#9ca3af", width=1.5),
        showlegend=False,
        hoverinfo="skip",
    ))
    tail = build_phase_line_frame(plot_frame[plot_frame["rhythm_day"] >= latest_day - pd.Timedelta(days=6)], circular=True)
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
        title=dict(text=_("chart_polar_title"), x=0.02, xanchor="left", font=dict(size=18)),
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
            ),
            radialaxis=dict(
                autorange=True,
                rangemode="tozero",
                gridcolor="#374151",
                linecolor="#6b7280",
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
def build_habit_observation(daily_points: pd.DataFrame, daily_summary: pd.DataFrame):
    if daily_points.empty or daily_summary.empty:
        return {
            "routine": "N/A",
            "routine_state": _("habit_variable"),
            "lock": "0",
            "disturbances": "0",
            "trend": _("habit_stable"),
            "recovery": _("recovery_none"),
        }
    recent_summary = daily_summary.sort_values("rhythm_day").tail(7)
    routine_column = recent_summary["routine_stability"] if "routine_stability" in recent_summary else pd.Series(dtype=float)
    routine_values = pd.to_numeric(routine_column, errors="coerce").dropna()
    routine_score = float(routine_values.mean()) if not routine_values.empty else None
    routine_state = _("habit_consistent") if routine_score is not None and routine_score >= 0.75 else _("habit_variable")
    routine_display = f"{routine_score:.0%}" if routine_score is not None else "N/A"
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
        "routine": routine_display,
        "routine_state": routine_state,
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


def plot_core_trend_charts(daily_points: pd.DataFrame, range_label: str):
    if daily_points.empty:
        st.info(_("info_no_trend_data"))
        return

    fig = build_core_trend_figure(
        daily_points,
        range_label,
        {
            "chart_wake": _("chart_wake"),
            "chart_sleep_debt": _("chart_sleep_debt"),
            "chart_habit": _("chart_habit"),
            "chart_routine_stability": _("chart_routine_stability"),
            "chart_date": _("chart_date"),
            "chart_title": _("chart_title"),
        },
    )
    if fig is None:
        st.info(_("info_no_trend_dates"))
        return
    st.plotly_chart(fig, width="stretch")



if "language_preference_loaded" not in st.session_state:
    st.session_state.lang = load_ui_settings()["lang"]
    st.session_state.language_preference_loaded = True
st.title(_("title"))
st.write(_("subtitle"))
st.caption(_("caption_naps"))


def initialize_test_parameter_state():
    if "test_target_wake" not in st.session_state:
        st.session_state.test_target_wake = datetime.strptime(load_ui_settings()["target_wake"], "%H:%M").time()
    if "test_sleep_need_hours" not in st.session_state:
        st.session_state.test_sleep_need_hours = float(load_ui_settings()["sleep_need_hours"])
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
        "lambda_d": float(config["lambda_d"]),
        "alpha_up": float(config["alpha_up"]),
        "alpha_down": float(config["alpha_down"]),
        "routine_wake_tau_hours": float(config.get("routine_wake_tau_hours", dynamics.ROUTINE_WAKE_TAU_HOURS)),
        "recovery_k": float(config["recovery_k"]),
        "recovery_saturation_tau": float(config["recovery_saturation_tau"]),
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
        save_ui_settings(ui_settings["attractor_p_limit"], ui_settings["attractor_d_limit"], ui_settings["target_utc_offset"], ui_settings["profile_id"])
        st.rerun()

    selected_profile_id = st.selectbox(
        _("profile_selector"),
        options=list(PROFILE_IDS),
        index=PROFILE_IDS.index(ui_settings["profile_id"]),
        format_func=profile_labels.__getitem__,
        key="profile_selector",
    )
    is_sample_profile = selected_profile_id in SAMPLE_PROFILE_IDS
    if is_sample_profile:
        st.caption(_("profile_read_only"))

    st.subheader("我的节律目标" if st.session_state.lang != "en" else "My schedule target")
    st.time_input(_("test_target_wake"), key="test_target_wake")
    st.number_input("睡眠时长参照（小时）" if st.session_state.lang != "en" else "Sleep duration reference (hours)", min_value=1.0, max_value=16.0, step=0.25, key="test_sleep_need_hours")
    st.caption("只设置希望几点起床和睡眠时长参照。相位与漂移自动计算；内部模型常数不是你的调参任务。" if st.session_state.lang != "en" else "Choose your wake target and sleep reference. Phase and drift are calculated automatically.")
    attractor_p_limit = float(config.get("attractor_p_limit", 1.0))
    attractor_d_limit = float(config.get("attractor_d_limit", 5.0))
    target_utc_offset = ui_settings["target_utc_offset"]
previous_profile_id = st.session_state.get("_recommendation_profile_id")
if previous_profile_id is None:
    recommendation_context_generation = 0
elif previous_profile_id != selected_profile_id:
    recommendation_context_generation = int(st.session_state.get("_recommendation_context_generation", 0)) + 1
else:
    recommendation_context_generation = int(st.session_state.get("_recommendation_context_generation", 0))
st.session_state["_recommendation_profile_id"] = selected_profile_id
st.session_state["_recommendation_context_generation"] = recommendation_context_generation


if (
    attractor_p_limit != ui_settings["attractor_p_limit"]
    or attractor_d_limit != ui_settings["attractor_d_limit"]
    or target_utc_offset != ui_settings["target_utc_offset"]
    or selected_profile_id != ui_settings["profile_id"]
    or st.session_state.test_target_wake.strftime("%H:%M") != ui_settings["target_wake"]
    or st.session_state.test_sleep_need_hours != ui_settings["sleep_need_hours"]
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

if daily_summary.empty:
    observer = {"P": None, "D": None, "H": None, "in_attractor": None, "rhythm_day": None}
else:
    observer = daily_summary.iloc[-1].to_dict()

latest_recommendation_point = daily_points.sort_values("rhythm_day").iloc[-1] if not daily_points.empty else None
recommendation_state = {**observer, "D": None}
recommendation_cbt_min = None
if latest_recommendation_point is not None:
    recommendation_sleep = latest_recommendation_point.get("sleep_hours")
    recommendation_wake = latest_recommendation_point.get("wake_time")
    if recommendation_wake and pd.notna(recommendation_sleep) and float(recommendation_sleep) > 0 and bool(observer.get("sleep_duration_known", True)):
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

st.markdown("<style>[data-stale=true]{opacity:1!important} [data-testid=stAppViewContainer] *{animation-duration:0s!important;transition-duration:0s!important}</style>", unsafe_allow_html=True)
st.header(_("today_title"))
recorded_day_statuses = classify_entry_dates(
    daily_summary,
    records_frame,
    daily_view,
    p_limit=attractor_p_limit,
)
calendar_css = build_date_input_calendar_css(recorded_day_statuses)
if calendar_css:
    st.markdown(calendar_css, unsafe_allow_html=True)
receipt_key = f"sleep_receipt:{selected_profile_id}"
chinese_entry = st.session_state.lang != "en"
calendar_column, entry_column = st.columns([1, 1.2])
with calendar_column:
    with st.container(key="entry_calendar"):
        selected_entry_day = render_entry_calendar(records_frame, recorded_day_statuses, selected_profile_id, chinese_entry)
with entry_column:
    render_daily_overview(daily_points, observer, chinese_entry)
    entry_slot = st.container()
selected_date_mask = records_frame["date"].astype(str).eq(str(selected_entry_day))
selected_records = records_frame.loc[selected_date_mask, RAW_COLUMNS].copy()
if not selected_records.empty:
    st.markdown(f"**{selected_entry_day} · {'已有记录（可修改）' if chinese_entry else 'Existing records (editable)'}**")
    corrected_records = st.data_editor(
        selected_records,
        key=f"entry_corrections:{selected_profile_id}:{selected_entry_day}:{hash(selected_records.to_csv(index=False))}",
        hide_index=True,
        num_rows="fixed",
        disabled=True if is_sample_profile else ["date"],
        column_config={
            "sleep_time": st.column_config.TextColumn(_("form_sleep_time")),
            "wake_time": st.column_config.TextColumn(_("form_wake_time")),
            "momentum": st.column_config.NumberColumn(_("form_momentum"), min_value=0, max_value=10),
        },
    )
    if st.button("保存该日修改" if chinese_entry else "Save corrections for this date", disabled=is_sample_profile):
        try:
            current_records = load_records_frame(active_data_file)
            if not current_records.equals(records_frame):
                raise ValueError("Records changed; refresh before editing.")
            normalized_corrections = normalize_raw_records(corrected_records)
            normalized_originals = normalize_raw_records(selected_records)
            changed_rows = normalized_corrections.ne(normalized_originals).any(axis=1)
            positive_windows = normalized_corrections["sleep_time"].ne(normalized_corrections["wake_time"])
            original_positive_windows = normalized_originals["sleep_time"].ne(normalized_originals["wake_time"])
            if bool((changed_rows & ~positive_windows & original_positive_windows).any()):
                raise ValueError("零睡眠请使用通宵入口 / Use the no-sleep option for zero sleep")
            untouched_records = current_records.drop(index=normalized_corrections.index[changed_rows])
            untouched_sleep = untouched_records[untouched_records["sleep_time"].ne(untouched_records["wake_time"])]
            validate_sleep_windows(normalized_corrections.loc[changed_rows & positive_windows], untouched_sleep, allow_long=True)
            corrected_frame = current_records.copy()
            corrected_frame.loc[selected_records.index, RAW_COLUMNS] = normalized_corrections[RAW_COLUMNS].to_numpy()
            _, _, _, corrected_persisted = rebuild_persisted_records(corrected_frame, active_params)
            save_records_frame(corrected_persisted, create_backup=True, path=active_data_file)
            st.session_state[receipt_key] = f"已保存 {selected_entry_day} 的修改，原数据已备份。" if chinese_entry else f"Saved corrections for {selected_entry_day}; original records backed up."
            st.session_state[f"{receipt_key}:toast"] = True
            st.rerun()
        except (OSError, ValueError, TypeError) as error:
            st.error(str(error))
if st.session_state.pop("daily_entry_reset_pending", False):
    st.session_state["daily_sleep_time"] = ""
    st.session_state["daily_wake_time"] = ""
    st.session_state["daily_no_sleep"] = False
    st.session_state["daily_momentum"] = 5
    st.session_state["daily_disturbance"] = False
    st.session_state["daily_medication"] = False
    st.session_state["daily_long_sleep_confirm"] = False
    st.session_state["daily_awake_minutes"] = 0
    st.session_state["daily_awake_unknown"] = False
receipt = st.session_state.get(receipt_key)
if receipt:
    st.success(receipt)
    if st.session_state.pop(f"{receipt_key}:toast", False):
        st.toast(receipt, icon="✅")
with entry_slot:
    st.subheader(_("today_log_title"))
    st.caption(_("today_log_caption"))
    chinese_entry = st.session_state.lang != "en"
    today = st.date_input(_("form_date"), value=None, key="daily_entry_date")
    no_sleep_entry = False
    no_sleep_day = today
    pending_key = f"no_sleep_confirmation:{selected_profile_id}"
    if st.session_state.get(pending_key) != str(no_sleep_day):
        st.session_state.pop(pending_key, None)
    if st.button("这天没睡（通宵）" if chinese_entry else "No sleep on this date", disabled=is_sample_profile or no_sleep_day is None, key="no_sleep_begin"):
        st.session_state[pending_key] = str(no_sleep_day)
    if pending_key in st.session_state:
        st.warning(f"确定将 {no_sleep_day} 提交为通宵吗？无需填写下方内容。" if chinese_entry else f"Confirm no sleep for {no_sleep_day}? No other fields required.")
        confirm_column, cancel_column = st.columns(2)
        if cancel_column.button("取消" if chinese_entry else "Cancel", key="no_sleep_cancel"):
            st.session_state.pop(pending_key, None)
            st.rerun()
        if confirm_column.button("确定提交通宵" if chinese_entry else "Confirm and save no sleep", type="primary", disabled=is_sample_profile, key="no_sleep_confirm"):
            current_records = load_records_frame(active_data_file)
            same_day = current_records["date"].astype(str).eq(str(no_sleep_day))
            if no_sleep_day > date.today() or same_day.any():
                st.error("该日期已有记录或是未来日期，请先核对日历。" if chinese_entry else "This date already has a record or is in the future. Check the calendar.")
            else:
                no_sleep_record = pd.DataFrame([{"schema_version": CURRENT_SCHEMA_VERSION, "date": no_sleep_day, "sleep_time": "00:00", "wake_time": "00:00", "momentum": None, "disturbance": 1, "sleep_medication": False, "awake_minutes": 0, "awake_unknown": False}])
                _, _, _, persisted = rebuild_persisted_records(pd.concat([current_records, no_sleep_record], ignore_index=True), active_params)
                save_records_frame(persisted, create_backup=False, path=active_data_file)
                st.session_state.pop(pending_key, None)
                st.session_state[receipt_key] = f"已记录 {no_sleep_day} 通宵。" if chinese_entry else f"Saved no sleep for {no_sleep_day}."
                st.rerun()
    with st.form("daily_entry", enter_to_submit=False):
        st.markdown("**记录睡眠 · 助眠药物在右侧一键勾选**" if chinese_entry else "**Log sleep · mark sleep-aid use on the right**")
        col1, col2 = st.columns(2)
        with col1:
            sleep_time = st.text_input(
                _("form_sleep_time"),
                placeholder="HH:MM or 830",
                help=_("form_time_help"),
                key="daily_sleep_time",
                disabled=no_sleep_entry,
            )
            wake_time = st.text_input(
                _("form_wake_time"),
                placeholder="HH:MM or 830",
                help=_("form_time_help"),
                key="daily_wake_time",
                disabled=no_sleep_entry,
            )
        with col2:
            momentum = st.slider(_("form_momentum"), 0, 10, 5, key="daily_momentum")
            disturbance = st.checkbox("其他重大扰动（生病、旅行等）" if chinese_entry else "Other major disturbance (illness, travel, etc.)", value=False, key="daily_disturbance")
            sleep_medication = st.checkbox(_("form_medication"), value=False, key="daily_medication", help=_("med_help"))
        with st.expander("中途醒来（可选）" if chinese_entry else "Awake during sleep (optional)"):
            awake_minutes_input = st.number_input("中途清醒合计分钟" if chinese_entry else "Total awake minutes", min_value=0, max_value=1440, step=5, key="daily_awake_minutes", disabled=no_sleep_entry)
            awake_unknown_input = st.checkbox("中途醒过，但不记得清醒总时长" if chinese_entry else "I was awake but do not know the total duration", key="daily_awake_unknown", disabled=no_sleep_entry)
            st.caption("填合计时长即可，不必逐次记录。" if chinese_entry else "Enter the total; individual awakening times are not required.")
        confirm_long_sleep = st.checkbox("若睡眠超过 16 小时，确认时间填写正确" if chinese_entry else "If sleep exceeds 16 hours, confirm the times are correct", key="daily_long_sleep_confirm")
        st.caption("Enter 确认并移到下一输入框；最后移到记录按钮。请明确点击按钮保存。" if chinese_entry else "Enter confirms and moves to the next field, then focuses the record button. Click the button to save.")
        submitted = st.form_submit_button(
            _("form_submit"),
            disabled=is_sample_profile,
            on_click=normalize_daily_entry_times,
        )

    if submitted:
        if today is None:
            st.error("请选择记录日期后保存。" if chinese_entry else "Choose a record date before saving.")
            st.stop()
        sleep_time = "00:00" if no_sleep_entry else normalize_clock_time(sleep_time)
        wake_time = "00:00" if no_sleep_entry else normalize_clock_time(wake_time)
        if sleep_time is None or wake_time is None:
            st.error(_("err_time_entry"))
            st.stop()
        if today > date.today():
            st.error("不能保存未来日期的实际睡眠记录。" if chinese_entry else "Actual sleep records cannot use a future date.")
            st.stop()
        session_start, session_end = dynamics.build_sleep_session(today, sleep_time, wake_time)
        entered_hours = dynamics.calculate_sleep_duration_hours(session_start, session_end)
        duration_minutes = int(round((session_end - session_start).total_seconds() / 60))
        duration_hours, remaining_minutes = divmod(duration_minutes, 60)
        duration_label = f"{duration_hours} 小时 {remaining_minutes} 分钟" if chinese_entry else f"{duration_hours} h {remaining_minutes} min"
        if not no_sleep_entry and entered_hours == 0:
            st.error("入睡与醒来时间相同。若确实没睡，请选择通宵入口。" if chinese_entry else "Identical times imply zero sleep. Use the no-sleep option if you did not sleep.")
            st.stop()
        if entered_hours > 16 and not confirm_long_sleep:
            st.error("睡眠超过 16 小时，请检查时间，并勾选确认后再保存。" if chinese_entry else "Sleep exceeds 16 hours. Check the times and confirm before saving.")
            st.stop()
        current_records = load_records_frame(active_data_file)
        if not no_sleep_entry:
            try:
                validate_sleep_windows(pd.DataFrame([{"date": today, "sleep_time": sleep_time, "wake_time": wake_time, "awake_minutes": awake_minutes_input, "awake_unknown": awake_unknown_input}]), allow_long=confirm_long_sleep)
            except ValueError as error:
                st.error(str(error))
                st.stop()
        duplicate_mask = (
            current_records["date"].astype(str).eq(str(today))
            & current_records["wake_time"].astype(str).eq(wake_time)
            & current_records["sleep_time"].astype(str).eq(sleep_time)
        ) if not current_records.empty else pd.Series(dtype=bool)
        if bool(duplicate_mask.any()):
            st.warning(_("err_duplicate_record"))
            st.stop()
        if not current_records.empty:
            existing_sessions = dynamics.derive_session_frame(current_records, active_params["target_wake"])
            if not no_sleep_entry:
                overlaps = existing_sessions[
                    (existing_sessions["sleep_hours"] > 0)
                    & (existing_sessions["sleep_start_dt"] < session_end)
                    & (existing_sessions["wake_end_dt"] > session_start)
                ]
                if not overlaps.empty:
                    st.error("这段睡眠与已有记录重叠，请在数据管理中更正原记录。" if chinese_entry else "This sleep overlaps an existing record. Correct the original in data management.")
                    st.stop()
            elif bool(((existing_sessions["date"] == today) & (existing_sessions["sleep_hours"] > 0)).any()):
                st.error("该日期已有睡眠记录，请先核对，避免矛盾的通宵声明。" if chinese_entry else "This date already has sleep records. Check them before declaring no main sleep.")
                st.stop()
        new_record = pd.DataFrame([{
            "schema_version": CURRENT_SCHEMA_VERSION,
            "date": today,
            "wake_time": wake_time,
            "sleep_time": sleep_time,
            "momentum": momentum,
            "disturbance": int(disturbance or no_sleep_entry),
            "sleep_medication": bool(sleep_medication),
            "awake_minutes": 0 if no_sleep_entry else awake_minutes_input,
            "awake_unknown": False if no_sleep_entry else awake_unknown_input,
            "P": None,
            "D": None,
            "H": None,
            "in_attractor": None,
        }])
        current_records = pd.concat([current_records, new_record], ignore_index=True)
        summary, derived, updated_daily_summary, persisted = rebuild_persisted_records(current_records, active_params)
        save_records_frame(persisted, create_backup=False, path=active_data_file)
        if not no_sleep_entry:
            net_minutes = duration_minutes - awake_minutes_input
            net_hours, net_remainder = divmod(net_minutes, 60)
            duration_label = f"{net_hours} 小时 {net_remainder} 分钟" if chinese_entry else f"{net_hours} h {net_remainder} min"
            if awake_unknown_input:
                duration_label += "（窗口上界，实际睡眠未知）" if chinese_entry else " (window upper bound; actual sleep unknown)"
        st.session_state[receipt_key] = (
            f"已保存 {today} 的通宵记录：主睡眠 0 小时，后续补觉可另行记录。" if no_sleep_entry and chinese_entry
            else f"Saved no-main-sleep record for {today}: 0 hours." if no_sleep_entry
            else f"已保存 {today} 的睡眠记录：{sleep_time} → {wake_time}，共 {duration_label}。" if chinese_entry
            else f"Saved sleep record for {today}: {sleep_time} → {wake_time}, {duration_label}."
        )
        st.session_state[f"{receipt_key}:toast"] = True
        st.session_state["daily_entry_reset_pending"] = True
        p_str = f"{summary['P']:.2f}" if pd.notna(summary.get("P")) else "N/A"
        st.write(_(
            "submit_state",
            day=summary["rhythm_day"],
            p=p_str,
            d=summary["D"],
            h=summary["H"],
            sleep=summary["sleep_hours"],
            sessions=summary["session_count"],
        ))
        st.rerun()

with entry_slot:
    render_medication_journal(selected_profile_id, st.session_state.get("daily_entry_date"), is_sample_profile, chinese_entry)

with st.expander("补录多段睡眠" if chinese_entry else "Add several sleep intervals"):
    st.subheader("多段睡眠批量补录" if chinese_entry else "Record several sleep intervals")
    st.caption("日期默认使用日历选中日，并表示每段醒来的日期；跨夜记录请核对日期。中途短暂醒来请用单段入口的清醒合计。" if chinese_entry else "Dates default to the selected calendar day and mean the wake date. Check overnight dates. Use awake totals for interruptions within one sleep.")
    batch_generation = st.session_state.get("sleep_batch_generation", 0)
    batch_context = f"{selected_profile_id}:{selected_entry_day}:{batch_generation}"
    batch_text = st.text_area("粘贴多段时间（可选）" if chinese_entry else "Paste intervals (optional)", placeholder="01:00-04:00; 05:00-09:00; 14:00-15:00", key=f"sleep_batch_paste:{batch_context}")
    try:
        batch_defaults = parse_sleep_intervals(batch_text, selected_entry_day)
        if batch_defaults.empty:
            batch_defaults = pd.DataFrame([{"date": selected_entry_day, "sleep_time": "", "wake_time": "", "awake_minutes": 0, "awake_unknown": False}])
        batch_defaults["date"] = pd.to_datetime(batch_defaults["date"]).dt.date
        batch_rows = st.data_editor(
            batch_defaults, num_rows="dynamic", hide_index=True,
            key=f"sleep_batch_editor:{batch_context}:{hash(batch_text)}",
            disabled=is_sample_profile,
            column_config={
                "date": st.column_config.DateColumn(_("form_date"), required=True),
                "sleep_time": st.column_config.TextColumn(_("form_sleep_time")),
                "wake_time": st.column_config.TextColumn(_("form_wake_time")),
                "awake_minutes": st.column_config.NumberColumn("清醒分钟" if chinese_entry else "Awake minutes", min_value=0, step=5),
                "awake_unknown": st.column_config.CheckboxColumn("清醒时长未知" if chinese_entry else "Awake time unknown"),
            },
        )
        batch_allow_long = st.checkbox("确认超过 16 小时的窗口" if chinese_entry else "Confirm windows exceeding 16 hours", key=f"sleep_batch_long:{batch_context}")
        batch_facts = batch_rows.copy()
        active_rows = batch_facts["sleep_time"].fillna("").astype(str).str.strip().ne("") | batch_facts["wake_time"].fillna("").astype(str).str.strip().ne("")
        batch_facts = batch_facts.loc[active_rows].copy()
        batch_facts["date"] = batch_facts["date"].fillna(selected_entry_day)
        batch_facts["momentum"] = 5
        batch_facts["disturbance"] = 0
        batch_facts["sleep_medication"] = False
        preview_valid = False
        if not batch_facts.empty:
            try:
                batch_facts = normalize_raw_records(batch_facts)
                windows = validate_sleep_windows(batch_facts, records_frame, batch_allow_long)
                preview_rows = []
                for row, (start, end) in zip(batch_facts.to_dict("records"), windows):
                    minutes = int((end - start).total_seconds() / 60 - row["awake_minutes"])
                    preview_rows.append({"date": row["date"], "interval": f'{start:%m-%d %H:%M} → {end:%m-%d %H:%M}', "sleep": f'{minutes // 60} h {minutes % 60} min', "certainty": "upper bound" if row["awake_unknown"] else "estimated sleep"})
                st.dataframe(pd.DataFrame(preview_rows), hide_index=True)
                total_minutes = sum(int((end - start).total_seconds() / 60 - row["awake_minutes"]) for row, (start, end) in zip(batch_facts.to_dict("records"), windows))
                st.caption(f"合计 {total_minutes // 60} 小时 {total_minutes % 60} 分钟" if chinese_entry else f"Total {total_minutes // 60} h {total_minutes % 60} min")
                timeline = go.Figure()
                for index, (row, (start, end)) in enumerate(zip(batch_facts.to_dict("records"), windows)):
                    timeline.add_trace(go.Scatter(x=[start, end], y=[index + 1, index + 1], mode="lines+markers", line={"width": 12}, name=f"{index + 1}", hovertemplate="%{x|%m-%d %H:%M}<extra></extra>"))
                timeline.update_layout(height=180 + 25 * len(windows), showlegend=False, xaxis={"title": "睡眠窗口" if chinese_entry else "Sleep windows", "type": "date"}, yaxis={"dtick": 1}, margin={"t": 15, "b": 35})
                st.plotly_chart(timeline, config={"displayModeBar": False})
                preview_valid = True
            except (TypeError, ValueError) as error:
                st.warning(str(error))
        if st.button("一次保存全部睡眠段" if chinese_entry else "Save all intervals", disabled=is_sample_profile or not preview_valid):
            current_batch_records = load_records_frame(active_data_file)
            validate_sleep_windows(batch_facts, current_batch_records, batch_allow_long)
            combined_records = pd.concat([current_batch_records, batch_facts], ignore_index=True)
            _, _, _, batch_persisted = rebuild_persisted_records(combined_records, active_params)
            save_records_frame(batch_persisted, create_backup=False, path=active_data_file)
            st.session_state[receipt_key] = f"已保存 {len(batch_facts)} 段睡眠，合计 {total_minutes // 60} 小时 {total_minutes % 60} 分钟。" if chinese_entry else f"Saved {len(batch_facts)} intervals: {total_minutes // 60} h {total_minutes % 60} min."
            if bool(batch_facts["awake_unknown"].any()):
                st.session_state[receipt_key] += " 含未知清醒时长，合计为上界。" if chinese_entry else " Includes unknown awake time; total is an upper bound."
            st.session_state[f"{receipt_key}:toast"] = True
            st.session_state["sleep_batch_generation"] = batch_generation + 1
            st.rerun()
    except (OSError, TypeError, ValueError) as error:
        st.error(str(error))
if not daily_summary.empty and bool(observer.get("state_estimated", False)):
    st.info("记录中有未知清醒时长：该窗口睡眠量为上界，债务轨迹仅为估计；更正后会重新计算。" if chinese_entry else "History includes unknown awake time: that window is an upper bound and the debt trajectory is estimated. Correct the record to recalculate.")
st.html("""
<script>
if (!window.mrdmEntryKeyboardInstalled) {
  window.mrdmEntryKeyboardInstalled = true;
  document.addEventListener('keydown', function(event) {
    if (event.key !== 'Enter' || event.isComposing || event.ctrlKey || event.altKey || event.metaKey) return;
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) return;
    const form = target.closest('[data-testid="stForm"]');
    if (!form || !form.querySelector('input[aria-label="Sleep Start (O2)"], input[aria-label="睡眠开始时间 (O2)"]')) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const fields = Array.from(form.querySelectorAll('[data-testid="stTextInput"] input')).filter(input => !input.disabled);
    const index = fields.indexOf(target);
    const next = index >= 0 ? fields[index + 1] : fields[0];
    if (next) { next.focus(); next.select(); }
    else { const button = form.querySelector('[data-testid="stFormSubmitButton"] button'); if (button) button.focus(); }
  }, true);
}
</script>
""", unsafe_allow_javascript=True)
primary_candidate = recommendation_candidates[0]
primary_action_name = localized_action_name(primary_candidate["action_type"])
primary_time = primary_candidate.get("recommended_time") or "N/A"
primary_duration = primary_candidate.get("recommended_duration_minutes")
st.markdown(f"**{_('today_action_title')}**")
st.success(f"### {primary_action_name}")
today_action_col1, today_action_col2 = st.columns(2)
today_action_col1.metric(_("today_action_when"), primary_time)
today_action_col2.metric(
    _("today_action_duration"),
    f"{primary_duration} min" if primary_duration not in (None, "") else "—",
)
st.caption(f"{_('today_action_reason')}: {_(primary_candidate['reason_key'])}")
st.caption(_("today_alternatives_hint"))
st.divider()
st.header(_("analysis_title"))

objective_ui.render_phase_objective(daily_points, active_params["sleep_need_hours"], st.session_state.lang != "en")
with st.expander("辅助观察：睡眠压力与历史分布" if st.session_state.lang != "en" else "Supporting observations: pressure and history"):
    pressure_ui.render_pressure_trajectory(daily_points, st.session_state.lang != "en")
st.subheader(_("charts_title"))
with st.expander("更多：长期作息模式" if chinese_entry else "More: longer-term patterns"):
    render_routine_patterns(daily_points, st.session_state.lang != "en")
with st.expander("可选：行动记录与 Jev 接口" if st.session_state.lang != "en" else "Optional: action journal and Jev"):
    recommendation_labels = []
    candidate_rows = []
    for candidate in recommendation_candidates:
        action_name = localized_action_name(candidate["action_type"])
        recommended_time = candidate.get("recommended_time") or "N/A"
        duration = candidate.get("recommended_duration_minutes")
        duration_label = f"{duration} min" if duration not in (None, "") else "—"
        recommendation_labels.append(f"{action_name} · {recommended_time}")
        candidate_rows.append({
            _("candidate_action"): action_name,
            _("candidate_time"): recommended_time,
            _("candidate_duration"): duration_label,
            _("candidate_basis"): _("candidate_rule_basis"),
        })
    st.dataframe(pd.DataFrame(candidate_rows), width="stretch", hide_index=True)

    if not is_sample_profile:
        st.markdown("---")
        st.markdown(f"**{_('recommendation_title')}**")
        st.caption(_("recommendation_caption"))
        selector_key = recommendation_selector_key(
            selected_profile_id,
            recommendation_state,
            recommendation_candidates,
            recommendation_context_generation,
        )
        if selector_key not in st.session_state:
            st.session_state[selector_key] = 0
        selected_candidate_index = st.selectbox(
            _("recommendation_title"),
            options=range(len(recommendation_candidates)),
            format_func=lambda index: recommendation_labels[index],
            key=selector_key,
        )
        selected_candidate = recommendation_candidates[selected_candidate_index]
        context_key = recommendation_context_key(
            selected_profile_id,
            recommendation_state,
            selected_candidate,
            recommendation_context_generation,
        )
        draft_keys = initialize_recommendation_draft_state(
            st.session_state,
            context_key,
            selected_candidate,
            active_params["target_wake"],
        )
        st.caption(_(selected_candidate["reason_key"]))
        st.markdown(f"**{_('jev_shadow_title')}**")
        st.caption(_("jev_shadow_caption"))
        jev_payload = build_jev_payload(
            recommendation_state,
            recommendation_candidates,
            [True] * len(recommendation_candidates),
        )
        with st.expander(_("jev_shared_title"), expanded=False):
            st.caption(_("jev_shared_caption"))
            st.markdown(f"**{_('jev_shared_state')}**")
            st.json(jev_payload["state"]["state"])
            st.markdown(f"**{_('jev_shared_candidates')}**")
            st.dataframe(pd.DataFrame(jev_payload["state"]["candidates"]), width="stretch", hide_index=True)
        jev_result_key = f"jev_shadow_result:{selector_key}"
        if st.button(_("jev_shadow_run"), key=f"jev_shadow_run:{selector_key}"):
            st.session_state[jev_result_key] = evaluate_jev(
                recommendation_state,
                recommendation_candidates,
                [True] * len(recommendation_candidates),
            )
        jev_result = st.session_state.get(jev_result_key)
        if jev_result:
            if jev_result["status"] == "disabled":
                st.info(_("jev_shadow_disabled"))
            elif jev_result["status"] == "unavailable":
                st.warning(_("jev_shadow_unavailable"))
            elif jev_result["status"] == "invalid":
                st.warning(_("jev_shadow_invalid"))
            elif jev_result["selection"] is None:
                st.info(_("jev_shadow_vetoed"))
            else:
                selected_jev_index = int(jev_result["selection"].split("_")[-1])
                selected_jev_candidate = recommendation_labels[selected_jev_index]
                if len(recommendation_candidates) == 1:
                    st.success(_("jev_shadow_single", candidate=selected_jev_candidate))
                    st.caption(_("jev_single_note"))
                else:
                    st.success(_("jev_shadow_preference", candidate=selected_jev_candidate))
                st.caption(_("jev_shadow_meaning"))
                assurance = min(jev_result["safety_noul"], jev_result["evidence_noul"])
                assurance_key = "jev_level_high" if assurance >= 0.8 else "jev_level_medium" if assurance >= 0.6 else "jev_level_low"
                st.metric(_("jev_assurance"), _(assurance_key))
                if jev_result["evidence_noul"] < 0.7:
                    st.warning(_("jev_low_evidence"))
                with st.expander(_("jev_technical_title"), expanded=False):
                    jev_col1, jev_col2, jev_col3 = st.columns(3)
                    jev_col1.metric(
                        _("jev_metric_confidence"),
                        f"{jev_result['confidence']:.0%}",
                        help=_("jev_help_confidence"),
                    )
                    jev_col2.metric(
                        _("jev_metric_safety"),
                        f"{jev_result['safety_noul']:.0%}",
                        help=_("jev_help_safety"),
                    )
                    jev_col3.metric(
                        _("jev_metric_evidence"),
                        f"{jev_result['evidence_noul']:.0%}",
                        help=_("jev_help_evidence"),
                    )
        st.markdown(f"**{_('empirical_log_title')}**")
        st.caption(_("empirical_log_caption"))
        with st.form(f"executed_intervention_form:{context_key}"):
            response_codes = ["completed", "partial", "accepted", "deferred", "not_completed", "declined", "not_seen"]
            response_labels = {_(f"response_{value}"): value for value in response_codes}
            response_label = st.selectbox(
                _("empirical_response"),
                list(response_labels),
                key=f"{context_key}:response",
            )
            response_input = response_labels[response_label]
            action_type_input = st.text_input(_("empirical_action_type"), key=draft_keys["action_type"])
            action_day_input = st.date_input(_("empirical_action_day"), key=draft_keys["action_day"])
            actual_time_input = st.time_input(_("empirical_actual_time"), key=draft_keys["actual_time"])
            duration_input = st.text_input(_("empirical_duration"), key=draft_keys["duration"])
            notes_input = st.text_input(_("empirical_notes"), key=draft_keys["notes"])
            save_action = st.form_submit_button(
                _("empirical_save_action"),
                key=f"{context_key}:submit",
            )
        if save_action:
            try:
                normalized_duration = duration_input.strip()
                recommended_duration = selected_candidate.get("recommended_duration_minutes")
                duration_modified = normalized_duration != ("" if recommended_duration in (None, "") else str(int(recommended_duration)))
                action_modified = action_type_input != selected_candidate["action_type"]
                time_modified = actual_time_input.strftime("%H:%M") != selected_candidate["recommended_time"]
                executed_response = response_input in {"completed", "partial"}
                stored_response = "modified" if response_input == "completed" and (action_modified or time_modified or duration_modified) else response_input
                planned_response = response_input in {"accepted", "deferred"}
                append_intervention({
                    "decision_id": decision_id_for_context(context_key),
                    "response": stored_response,
                    "rhythm_day": action_day_input.strftime("%Y-%m-%d"),
                    "action_type": action_type_input,
                    "recommended_time": selected_candidate["recommended_time"],
                    "planned_time": actual_time_input.strftime("%H:%M") if planned_response else "",
                    "actual_time": actual_time_input.strftime("%H:%M") if executed_response else "",
                    "duration_minutes": duration_input.strip() if executed_response else "",
                    "executed": executed_response,
                    "source": "user_report",
                    "notes": notes_input,
                })
                st.success(_("empirical_action_saved"))
            except (OSError, TypeError, ValueError) as error:
                st.error(_("empirical_action_error", error=error))


active_params = get_active_parameters()

with st.expander("数据管理与导入导出" if st.session_state.lang != "en" else "Data management and import/export"):
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
