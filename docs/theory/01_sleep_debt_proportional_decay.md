# Sleep Debt: Proportional Decay Model

Version: v0.5

---

## S2. Sleep Debt (D) — Slow Variable

Cumulative physiological recovery demand with integrating effect.

$$
D_t = \lambda D_{t-1} + (SleepNeed - SleepActual)
$$

Recommended $\lambda = 0.9$. Range: $0 \le D \le +\infty$ (debt never negative).

When oversleep occurs ($SleepActual > SleepNeed$), recovery follows a proportional saturation curve against current debt:

$$
\Delta D_{recovery} = -D_{t-1} \cdot k \cdot \left(1 - e^{-(SleepActual - SleepNeed) / \tau}\right)
$$

$$
D_t = \max\left(0, \lambda D_{t-1} + \Delta D_{recovery}\right)
$$

Parameters:
- $k = 0.4$ — single long sleep recovers max $40\%$ of current debt; $D=12 \to 7.2$, needs ~3 nights to drop below 1
- $\tau = 2.0$ — saturation rate: oversleep 2h reaches ~$63\%$ of $k \cdot D_{t-1}$

## Research Basis

| Reference | Key Insight | Impact |
|---|---|---|
| Van Dongen et al. (2003) | Chronic restriction deficits equal total deprivation | Proportional over absolute recovery |
| Banks & Dinges (2010) | 1–2 recovery nights insufficient | Multi-night decay with $k=0.4$ |
| Yamazaki et al. (2021) | Single recovery sleep insufficient | Fractional per-night decay |
| Ochab et al. (2021) | Recovery follows exponential decay | Directly motivates proportional formula |

See `reference/banks2010.md`, `reference/ochab2021.md`, `reference/vandongen2003.md`, `reference/yamazaki2021.md`.