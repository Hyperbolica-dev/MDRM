# Changelog

All notable changes to MRDM are recorded here in a maintenance-friendly format.

## [Unreleased]

### Added

- English-only project README consolidated into `README.md`.
- Raw-data review and manual management section in the console UI.
- Rhythm-day aggregation rule anchored to `WakeTarget`.
- Short in-app explanation of the current P / D / H calculation principles.

### Changed

- Sleep sessions are now grouped by rhythm day instead of being treated as a single natural-day sleep block.
- Daily summaries are computed from aggregated sleep sessions so naps and split sleep are handled consistently.
- The Streamlit UI can edit or delete raw records and creates a backup before saving changes.
- Rhythm-day attribution is now based on sleep start time relative to `WakeTarget`: sessions that start before the target stay in the current day, and sessions that start at or after the target roll into the next day.

### Fixed

- Stale module loading in the Streamlit app was guarded with a reload so newly added model helpers are available after updates.

## [2026-07-13]

### Notes

- Established the current MRDM console workflow around a Python/Streamlit prototype and the MRDM rhythm model.
- Introduced the first rhythm-day aware state computation for the current implementation.