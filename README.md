# MRDM Console v0.1

MRDM (Minimal Rhythm Dynamics Model) is a minimal, long-running rhythm control system for a single subject (N=1). The repository currently contains a Python/Streamlit prototype that supports low-cost daily logging and rhythm tracking.

MRDM is not about micro-level prediction accuracy. It focuses on stability over time: stable attractors, fast recovery after disturbance, and sustainable operation for months.

## What it tracks

- Sleep and wake timing
- Sleep debt
- Habit strength
- Recovery after disturbance

## Core rule

Daily data is grouped by a rhythm day anchored to `WakeTarget`.

- Sleep sessions that start before `WakeTarget` belong to the current rhythm day.
- Sleep sessions that start at or after `WakeTarget` belong to the next rhythm day.
- Multiple sleep sessions in one rhythm day are summed by duration.
- `P` is based on the end time of the main sleep session in that rhythm day.

## Current behavior

The Streamlit console lets you:

- enter one daily record in under 10 seconds,
- review and edit raw records,
- delete mistakes and save a backup,
- see derived `P`, `D`, `H`, and attractor status.

## Calculation notes

- `P` uses the main sleep session end time versus `WakeTarget`.
- `D` sums all sleep sessions in the rhythm day and then applies the decay rule.
- `H` rises slowly near target phase and decays quickly when phase drifts away.

The formal model is documented in [MRDM.md](MRDM.md).

## Run

From the project root:

```bash
bash start_mrdm.sh
```

## Files

- `README.md`: this overview.
- `CHANGELOG.md`: maintenance log.
- `MRDM.md`: model specification.
- `ui/streamlit_app.py`: current UI.
- `model/dynamics.py`: current state calculations.
- `data/records.csv`: daily history.

## Deferred work

- Phase response curve correction
- Control cost penalties
- More detailed pharmacological modeling

These ideas are valid, but their measurement cost or parameter uncertainty is too high for the minimal v0.1 control loop.
