# MRDM Console v0.4

MRDM (Minimal Rhythm Dynamics Model) is a minimal, long-running rhythm control system for a single subject (N=1). The repository currently contains a Python/Streamlit prototype that supports low-cost daily logging, rhythm tracking, and attractor-state diagnosis.

MRDM is not about micro-level prediction accuracy. It focuses on stability over time: stable attractors, fast recovery after disturbance, and sustainable operation for months.

## What it tracks

- Sleep and wake timing
- Sleep debt
- Habit strength
- Phase offset from the target rhythm
- Recovery after disturbance

## Core rule

Daily data is grouped by a rhythm day anchored to `WakeTarget`.

- Overnight sleep belongs to the wake date.
- Same-day evening sleep belongs to the next rhythm day.
- Multiple sleep sessions in one rhythm day are summed by duration.
- `P` is based on the mid-sleep time (MSM) of the main sleep session in that rhythm day.
- A zero-sleep (all-nighter) rhythm day leaves `P` undefined, adds the full sleep need to the debt, and decays habit strength quickly.

## Current behavior

The Streamlit console lets you:

- enter one daily record in under 10 seconds,
- mark whether a sleep-aid medication was used,
- open a test panel to temporarily override target wake time, sleep need, and dynamics parameters,
- review and edit raw records,
- delete mistakes and save a backup,
- see derived `P`, `D`, `H`, and attractor status,
- read a live attractor-state diagnosis (steady lock / social jetlag / acute deprivation / phase advance / rhythm drift),
- explore the P-D phase-space trajectory with temporal fading and attractor-zone highlighting,
- open an interactive guide on how to read the phase-space chart.

## Calculation notes

- `P` is the phase offset of the mid-sleep time (MSM): `P = M_actual - M_target`, where `M_actual = T_wake - SleepDuration/2` and `M_target = WakeTarget - SleepNeed/2`.
- `D` sums all sleep sessions in the rhythm day, then applies a proportional decay rule.
- `H` rises slowly near target phase and decays quickly when phase drifts away.

The formal model is documented in [MRDM.md](MRDM.md).

## v0.5 research

Closed-loop control research — light-therapy phase correction driven by the Khalsa (2003) phase response curve and an implicit `CBT_min` estimate — is documented in [docs/THEORY_RESEARCH.md](docs/THEORY_RESEARCH.md). Literature reference cards live in `reference/`, and the control simulation lives in `scripts/simulate_control.py`.

## Setup

```bash
conda env create -f environment.yaml
conda activate mrdm
```

Or with mamba (recommended for faster dependency resolution):

```bash
mamba env create -f environment.yaml
mamba activate mrdm
```

## Run

From the project root:

```bash
bash start_mrdm.sh
```

The app auto-initializes an empty `data/records.csv` on first launch.

Edit `config.yaml` to set your target wake time and sleep need before starting.

## Files

- `README.md`: this overview.
- `CHANGELOG.md`: maintenance log.
- `MRDM.md`: model specification.
- `docs/THEORY_RESEARCH.md`: closed-loop control theory research (v0.5).
- `ui/streamlit_app.py`: current UI.
- `model/dynamics.py`: current state calculations.
- `reference/`: literature reference cards.
- `scripts/simulate_control.py`: PRC control simulation.
- `config.yaml`: user configuration.

## Deferred work

- Control cost penalties
- More detailed pharmacological modeling
- Light-therapy recommendation UI (research ready; see `docs/THEORY_RESEARCH.md`)
