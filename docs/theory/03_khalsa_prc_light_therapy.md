# Khalsa (2003) PRC Light Therapy Control Law

Version: v0.5

---

## PRC Mathematical Form

Phase origin: $\widehat{CBT}_{\min} = 0$

Phase angle:
$$
\Delta\phi = T_{light} - \widehat{CBT}_{\min} \in [-12, 12)
$$

Continuous sinusoidal PRC (amplitude scaled by light saturation):

$$
f(\Delta\phi) =
\begin{cases}
0, & |\Delta\phi| > 6 \\
-A \cdot \sin\left(\dfrac{\pi \Delta\phi}{6}\right), & |\Delta\phi| \le 6
\end{cases}
$$

$$
A = \min\left(1.2\,\text{h},\ 1.2\,\text{h} \cdot \frac{lux}{10000}\right)
$$

Sign convention:
- **Delay zone** $\Delta\phi \in [-6, 0)$: $f > 0$, phase shifts right ($P$ increases)
- **Advance zone** $\Delta\phi \in (0, 6]$: $f < 0$, phase shifts left ($P$ decreases)
- **Dead zone** $\Delta\phi = 0$: $f = 0$

Peak response at $\Delta\phi = \pm 3\,\text{h}$ (delay $+1.2$h / advance $-1.2$h), matching Khalsa (2003) observed 2–4h windows around $CBT_{\min}$. Borders $\pm 6$h go to zero (daylight has negligible phase effect).

---

## Proportional Control Law

Avoids constant-step overshoot via **proportional control + deadband**:

$$
U_t = g(P_t) =
\begin{cases}
T_{light} = \widehat{CBT}_{\min} + 3 \cdot \min\!\left(1,\ \dfrac{P_t - \delta}{2}\right), & P_t > \delta \\[6pt]
T_{light} = \widehat{CBT}_{\min} - 3 \cdot \min\!\left(1,\ \dfrac{|P_t| - \delta}{2}\right), & P_t < -\delta \\[6pt]
\varnothing\ (\text{no light}), & |P_t| \le \delta
\end{cases}
$$

- $\delta = 0.5\,\text{h}$: deadband, stops intervention inside $|P| \le \delta$ to avoid limit cycling
- Max offset $3$h (PRC peak), linearly scaled by deviation $|P| - \delta$
- Large phase deviation → near-peak window (fast convergence); small deviation → off-peak (smooth approach, no overshoot)

---

## State Update

$$
P_{t+1} = P_t + f(\Delta\phi_t) + \eta P_t
$$

$$
D_{t+1} = \lambda_d D_t - k D_t \left(1 - e^{-(S_t - N)/\tau}\right),\quad S_t = N + \min(2, 0.3 D_t)
$$

- $\eta$: natural phase relaxation rate without light ($-0.1/\text{day}$ simulating weak entrainment; $\eta=0$ under light therapy)
- Parameters from config: $\lambda_d=0.9$, $k=0.4$, $\tau=2.0$, $N=7.0$h, $WakeTarget=08:30$

---

## Simulation Validation

### Setup
- Window: 7 rhythm days
- Intensity: $lux = 10000$ (bright light / therapy lamp), $A = 1.2$h
- Scenario 1: Social jetlag $P=+3.0$, $D=4.0$, morning light
- Scenario 2: Severe deprivation $P=-3.0$, $D=6.0$, evening light
- Scenario 3: Control $P=+3.0$, $D=4.0$, no light ($\eta=-0.1$)

### Results
| Scenario | Convergence | Day in attractor | Key observation |
|---|---|---|---|
| 1 (morning light) | Yes | Day 3 | $\Delta P$ shrinks nonlinearly ($-1.20 \to -1.02 \to -0.26 \to -0.02$) |
| 2 (evening light) | Yes | Day 4 | Same convergence profile, slower due to higher initial $D$ |
| 3 (no light) | No | — | $P=1.43$ at day 7, still outside attractor |

### Conclusions
1. **Nonlinear convergence confirmed**: Proportional control + sine PRC produces asymptotic curve, not constant-step
2. **Light therapy accelerates convergence**: Scenarios 1–2 enter attractor; Scenario 3 does not
3. **No overshoot**: Deadband $\delta=0.5$ stops intervention, $P$ settles smoothly at $0.50$, no limit cycle
4. **Sign correctness**: Morning light ($\Delta\phi>0$) drives $P$ left; evening light ($\Delta\phi<0$) drives $P$ right — consistent with Khalsa (2003)

---

## Implementation Advice for v0.5+

1. **Control functions** (already in `model/dynamics.py`):
   - `estimate_cbt_min(wake, sleep)` — $MSM + 1.5$h, zero-friction
   - `prc_shift(cbt_min, light_hour, lux)` — continuous sine Khalsa PRC
2. **Control law** (`scripts/simulate_control.py`): proportional + deadband, anchored to $\widehat{CBT}_{\min}$
3. **UI integration**: Dashboard displays "today's light therapy window" $[T_{light} \pm 0.5]$h; no recording checkbox (implicit feedback via next-day $P$)
4. **Needs empirical calibration**: $A$ lux saturation curve, $\eta$ (natural relaxation), deadband $\delta$ — requires N=1实测 data fitting

---

## References

| Reference | Key Insight | Impact |
|---|---|---|
| Khalsa et al. (2003) | Human single-bright-light PRC: delay peak before CBT_min, advance peak after, magnitude ~1.0–1.5h | Defines $\widehat{CBT}_{\min}$ origin and continuous sine PRC $f(\Delta\phi)$, drives light therapy control law |

See `reference/khalsa2003.md`.