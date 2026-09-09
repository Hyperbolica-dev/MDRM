# Polar Phase Space Topology and Attractor Zone Partitioning

Version: v0.5

---

## State Space Partitioning

The $(P, D)$ plane maps to deterministic control rules:

| Zone | $P$ range | $D$ range | Intervention rule |
|---|---|---|---|
| A. Steady lock | $\|P\| \le 1.0$ | $D \le 2.0$ | No intervention, maintain rhythm |
| B. Phase delay (social jetlag) | $P > 1.0$ | $D \le 5.0$ | Morning light: $T_{light} = \widehat{CBT}_{\min} + 3$h (advance) |
| C. Phase advance | $P < -1.0$ | $D \le 5.0$ | Evening light: $T_{light} = \widehat{CBT}_{\min} - 3$h (delay) |
| D. Acute sleep debt | $\|P\| \le 1.0$ | $D > 5.0$ | Extend sleep window (debt first), light therapy auxiliary |
| E. Compound perturbation | $\|P\| > 1.0$ | $D > 5.0$ | Dual channel: debt recovery + phase light therapy |
| F. Uncertain phase | $\|P\| > 6.0$ or $P=\text{None}$ | Any | No light therapy, sleep window only |

The formal attractor uses runtime thresholds with defaults $|P|<1.0$, $D<5.0$ and requires seven consecutive rhythm days. The tighter $D\le2.0$ region remains a control-analysis zone, not the formal status boundary.

---

## Attractor Definition (Core Model)

From `docs/MRDM.md` §7:

**Attractor**: When $|P| < 1$h and $D < 5$h, maintained for 7+ consecutive days, system declares `IN ATTRACTOR`.

**Robustness measure**: Days required to return to `IN ATTRACTOR` after perturbation ($DIS_t=1$) — recovery time $R$. The runtime summary reports this as `recovery_days` on the disturbance event when re-entry is observed.

---

## Polar Coordinate Mapping Rationale

$P$ is inherently circular (mod 24h). Cartesian coordinates create artificial boundary effects at $\pm 12$h:
- $P = +11$h and $P = -13$h are equivalent but appear far apart
- Trajectories that cross the $\pm 12$h seam produce misleading visual jumps

Polar mapping:
- **Angle**: normalized phase offset $\theta = \pi \cdot P / 12$ (range $-\pi$ to $\pi$)
- **Radius**: sleep debt $D$ (range $0$ to $+\infty$)
- **12 o'clock**: target phase $P = 0$ (aligned rhythm)
- **Clockwise from 12**: delay zone ($P > 0$); **counter-clockwise**: advance zone ($P < 0$)

This preserves circular topology and eliminates the $\pm 12$h boundary seam.
