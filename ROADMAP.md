# MRDM Roadmap

## Version Convention

| Level | Trigger | Example |
|---|---|---|
| Major | `records.csv` schema incompatible | v0.4 → v1.0 |
| Minor | Theory model update | v0.4 → v0.5 |
| Patch | Programmatic feature / tooling update | v0.5.0 → v0.5.1 |

---

## Current: v0.5.x stabilization

- Persistent target UTC-offset setting and dashboard biological UTC estimate based on the latest seven valid phase observations.
- Provisional live-state display for assumed awake time, missed sleep window, and projected debt without record mutation.

### v0.5.1 — Light Therapy Guidance UI

Dashboard passively displays:
- $\widehat{CBT}_{\min}$ estimate (based on MSM + 1.5h)
- Today's light window recommendation $[T_{light} \pm 0.5$h]

No new recording fields. No UI checkboxes. Closed-loop feedback via next-day $P$ trajectory.

### v0.5.2 — Polar Coordinate Phase Chart

- New `draw_polar_phase_chart()` function
- Toggle switch between Cartesian and polar views
- Polar: angle = $P$, radius = $D$
- Preserves tooltip, opacity decay, attractor zone coloring

---

## Future Research Directions

- **Control cost in objective function**: Add $-\delta \sum |U_t|$ to penalize over-reliance on forced wake or medication (weight $\delta$ needs empirical calibration)
- **Pharmacological modeling**: Extend medication layer beyond sleep-aid 0/1; dose-response curves
- **Multi-subject expansion**: Parameter variation across subjects; group-level attractor statistics
- **Density-based attractor estimation**: Replace rectangular attractor heuristic with KDE from $>60$ days data
- **H to phase space**: Encode habit strength $H$ as point size or border width on phase chart
- **Perturbation markers**: Distinct markers for $DIS=1$ points on trajectory; recovery time $R$ annotations
