# MRDM Console v0.5

MRDM (Minimal Rhythm Dynamics Model) is a minimal, long-running rhythm control system for a single subject (N=1). The repository contains a Python/Streamlit prototype supporting low-cost daily logging, rhythm tracking, attractor-state diagnosis, and closed-loop light therapy guidance (v0.5).

MRDM is not about micro-level prediction accuracy. It focuses on stability over time: stable attractors, fast recovery after disturbance, and sustainable operation for months.

## What it tracks

- Sleep and wake timing
- Sleep debt
- Habit strength
- Phase offset from the target rhythm
- Recovery after disturbance
- CBT_min estimation and light therapy window (v0.5.1)
- Estimated biological UTC offset from the latest seven valid phase observations
- Provisional live awake time and debt projection before the next sleep record

## Core rule

Daily data is grouped using a fixed 18:00 rhythm-day boundary.

- Overnight sleep belongs to the wake date.
- Same-day evening sleep belongs to the next rhythm day.
- Multiple sleep sessions in one rhythm day are summed by duration.
- `P` uses the representative main sleep wake time and total sleep across that rhythm day.
- Missing rhythm days between the first and last records are inferred as all-nighters; days after the last record are not inferred.
- A zero-sleep (all-nighter) rhythm day leaves `P` undefined, adds the full sleep need to the debt, and decays habit strength quickly.

## Current behavior

The Streamlit console lets you:

- enter one daily record in under 10 seconds,
- mark whether a sleep-aid medication was used,
- open a test panel to temporarily override target wake time, sleep need, and dynamics parameters,
- review and edit raw records,
- delete mistakes and save a backup,
- see derived `P`, `D`, `H`, and seven-day attractor status with persistent runtime thresholds,
- read a live attractor-state diagnosis (steady lock / social jetlag / acute deprivation / phase advance / rhythm drift),
- explore the P-D phase-space trajectory (Cartesian or polar) with temporal fading and attractor-zone highlighting,
- see estimated CBT_min and today's light therapy window (v0.5.1).
- set the target rhythm's UTC offset and see an estimated biological UTC offset.

## Calculation notes

- `P` is the phase offset of the mid-sleep time (MSM): `P = M_actual - M_target`, where `SleepDuration` is total rhythm-day sleep.
- `D` sums all sleep sessions in the rhythm day, then applies a proportional decay rule.
- `H` rises slowly near target phase and decays quickly when phase drifts away.

The formal model is documented in [docs/MRDM.md](docs/MRDM.md). Theory specs live in `docs/theory/`.

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
bash scripts/start_mrdm.sh
```

The app auto-initializes an empty `data/records.csv` on first launch.

Edit `config.yaml` to set your target wake time and sleep need before starting.

## Files

| Path | Purpose |
|---|---|
| `README.md` | this overview |
| `CHANGELOG.md` | maintenance log |
| `ROADMAP.md` | version roadmap and future directions |
| `docs/MRDM.md` | model specification |
| `docs/theory/` | modular theory specs (sleep debt, MSM phase, PRC control, polar topology) |
| `ui/streamlit_app.py` | Streamlit UI |
| `model/dynamics.py` | state calculations |
| `reference/` | literature reference cards |
| `scripts/simulate_control.py` | PRC control simulation |
| `scripts/start_mrdm.sh` | launcher script |
| `config.yaml` | user configuration |

## Deferred work

- Control cost penalties
- Pharmacological modeling beyond sleep-aid 0/1
- Density-based attractor estimation (replace rectangular heuristic)
- Multi-subject expansion

See `ROADMAP.md` for the full plan.
