# Changelog

All notable changes to MRDM are recorded here in a maintenance-friendly format.

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