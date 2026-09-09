# Changelog

All notable changes to MRDM are recorded here in a maintenance-friendly format.

## [v0.5.4] - Unreleased

### Added

- Disturbance markers and recovery-duration reporting in P-D trajectories.
- Habit-observation cards for wake consistency, attractor lock streak, disturbance count, and H trend.
- Phase-space markers distinguish daily target membership from formal consecutive-day attractor lock.
- Versioned intervention persistence that keeps recommendations separate from explicit execution reports.
- Circular chronological transition features, persistence baselines, Gaussian-process forecasts, and walk-forward validation.
- Experimental shadow-controller status panel with uncertainty, action-support gating, and executed-intervention logging.

### Changed

- Cartesian P-D remains the operational default; the polar seam view remains optional and advanced.
- Controller eligibility now requires predictive validation and identifiable executed-action support instead of geometric P-D ranking.

## [v0.5.3] - 2026-08-28

### Added

- Actionable non-light guidance when phase is uncertain beyond the safe light-therapy range.
- Prominent rhythm observation conclusions based on current P/D state.
- Sidebar profile selector with personal records and four generated read-only sample profiles: stable rhythm, phase delay, sleep debt, and phase advance.

### Changed

- Selected profiles use isolated record files and recalculate the complete observer state on every switch.


## [v0.5.2] - 2026-07-31

### Added

- Polar coordinate P-D chart with a Cartesian/polar toggle.
- Persistent target UTC-offset input and a seven-observation circular biological UTC estimate.
- Provisional live-state panel driven by target-local system time and the last recorded wake.

### Changed

- Replaced spline interpolation with discrete straight segments and direction markers.
- Moved trajectory direction markers from segment midpoints to segment endpoints.
- Polar hover now reports phase offset in hours.

### Fixed

- Preserved persisted attractor thresholds when active test parameters are refreshed before record submission.
- Split dashboard metrics across two rows so labels and values remain fully visible.

## [v0.5.1] - 2026-07-31

### Added

- Passive CBT_min estimation and light-window guidance without new recording fields.
- Safe mode suppresses light guidance when phase is undefined or `|P| > 6h`.

## [v0.5] - 2026-07-31

### Added

- `ROADMAP.md`: version numbering convention and planned release roadmap.
- `docs/theory/`: modular theory spec files (sleep debt proportional decay, MSM phase offset + CBT_min estimation, Khalsa PRC light therapy control law, polar phase space topology).
- Seven-day consecutive attractor detection with persistent runtime P/D thresholds.
- Internal missing rhythm days are inferred as all-nighters without extrapolating after the final record.

### Changed

- File structure reorganized:
  - `MRDM.md` → `docs/MRDM.md`
  - `references.md` → `reference/references.md`
  - `start_mrdm.sh` → `scripts/start_mrdm.sh`
  - `tasks.md` removed (archived content superseded by ROADMAP.md)
  - `docs/THEORY_RESEARCH.md` removed (content split into `docs/theory/`)
- AGENTS.md: updated file paths and added version numbering section.
- README.md: updated to v0.5, new file structure table.

## [v0.4] - 2026-07-30

### Changed

- Phase offset $P$ calculation refactored from wake-target-only to **Sleep Midpoint (MSM)** model: $P = M_{actual} - M_{target}$, where $M_{actual} = T_{wake} - SleepDuration/2$ and $M_{target} = WakeTarget - SleepNeed/2$. Proper 24-hour wrap-around handling applied.
- P-D phase space trajectory chart updated: line segments now use **spline interpolation** (`shape='spline'`, `smoothing=1.3`) instead of arrow annotations, with **temporal opacity decay** ($\text{opacity} = \max(0.15, e^{-0.3 \Delta t})$) so older points fade into the background.

### Added

- **Zero-sleep / all-nighter edge case**: When `SleepDuration == 0`, phase offset $P$ is set to `None` (exempt from MSM calculation), full `SleepNeed` is added to sleep debt without recovery decay, and habit strength $H$ decays rapidly via `alpha_down`.
- **Attractor State Interpreter**: Dynamic diagnosis panel below the P-D phase space chart evaluates current $(P, D, H)$ with color-coded status card (稳态锁定 / Social Jetlag / Acute Deprivation / Phase Advance / Rhythm Drift) and convergence indicator (收敛中 / 离心漂移中).
- **Interactive guide expander** (`"📖 如何阅读 P-D 相图与吸引子？"`) explaining X/Y axes, attractor zone, temporal fading, and quadrant definitions.

## [v0.3-nightly] - 2026-07-28

### Changed

- Replaced `st.time_input` with `st.text_input` in daily entry form to remove dropdown time-picker popup. Swapped input order (sleep before wake) to match natural entry flow. Added HH:MM format validation on submit.
- Sleep debt recovery changed from absolute (`R_max=3.0`, fixed cap per night) to proportional (`k=0.4`, recovers k*D of current debt). Addresses chronic debt not clearing in 1-2 nights per Van Dongen (2003) et al.

### Added

- English-only project README consolidated into `README.md`.
- Raw-data review and manual management section in the console UI.
- Rhythm-day aggregation rule anchored to `WakeTarget`.
- Short in-app explanation of the current P / D / H calculation principles.
- Sleep-aid medication checkbox in the daily entry form.
- Test panel for temporary overrides of target wake time, sleep need, and dynamics parameters.
- Automatic daily backup creation on first launch, plus backup retention cleanup.
- Primary state observer dashboard with current P, D, H, and attractor status.
- P-D phase-space trajectory view with attractor zone highlighting and current-state emphasis.
- Core trend charts for wake time, sleep debt, and habit strength with time-range controls.
- CSV import validation with schema-version, required-column, and date-format checks.

### Changed

- Replaced matplotlib with Plotly for the P-D phase-space trajectory view and core trend charts. Adds interactive hover tooltips showing date, P, D, H, wake time, sleep hours, momentum, disturbance, and attractor status per data point. Removes matplotlib as a runtime dependency.
- Daily summaries are computed from aggregated sleep sessions so naps and split sleep are handled consistently.
- The Streamlit UI can edit or delete raw records and creates a backup before saving changes.
- Rhythm-day attribution is now anchored to the wake date for overnight sleep, while same-day evening sleep rolls into the next rhythm day.
- The console now behaves as a rhythm state observer landing page instead of a raw log viewer.
- The rectangular attractor overlay is treated as a temporary heuristic for future density-based analysis.

### Fixed

- Stale module loading in the Streamlit app was guarded with a reload so newly added model helpers are available after updates.

## [2026-07-13]

### Notes

- Established the current MRDM console workflow around a Python/Streamlit prototype and the MRDM rhythm model.
- Introduced the first rhythm-day aware state computation for the current implementation.
