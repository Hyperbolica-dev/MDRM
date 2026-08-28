# Mid-Sleep Phase Offset and Implicit CBT_min Estimation

Version: v0.5

---

## S1. Circadian Phase (P) — Slow Variable

Phase offset relative to target rhythm, based on **Mid-Sleep Time (MSM)** model.

Target mid-sleep:
$$
M_{target} = WakeTarget - \frac{SleepNeed}{2}
$$

Actual mid-sleep uses the total duration of all sleep sessions in the rhythm day, including naps and split sleep:
$$
M_{actual} = T_{wake} - \frac{SleepDuration}{2}
$$

Phase offset:
$$
P_t = M_{actual} - M_{target}
$$

$P_t$ is folded to $[-12, 12)$ hour range modulo 24.

When $SleepDuration = 0$ (all-nighter), $P_t$ is undefined (marked `None`), excluded from $H$ phase constraint; full $SleepNeed$ enters $D_t$ without recovery decay; $H_t$ decays rapidly.

Unit: hour.

---

## Implicit CBT_min Estimation (Zero-Friction Observation)

Classic PRC requires core body temperature minimum ($CBT_{\min}$) as phase origin, which needs continuous rectal/implantable measurement — violating the 10-second recording constraint.

### Estimation Formula

Leverages stable phase relationship between MSM and $CBT_{\min}$:

$$
MSM = T_{wake} - \frac{SleepDuration}{2}
$$

$$
\widehat{CBT}_{\min} = MSM + 1.5\ \text{hours}
$$

All inputs from existing observations (O1/O2), no additional recording.

### Phase Folding

$MSM$, $\widehat{CBT}_{\min}$ both folded to $[-12, 12)$ hour range for 24-hour circular correctness:

$$
\widehat{CBT}_{\min} \leftarrow \widehat{CBT}_{\min} - 24\lfloor (\widehat{CBT}_{\min} + 12)/24 \rfloor
$$

### Robustness Under Extreme Perturbation

**All-nighter** ($SleepDuration = 0$): $P_t = \text{None}$, $MSM$ undefined. $CBT_{\min}$ marked inestimable; light therapy suspended; enters debt recovery mode until next valid main sleep.

**Social jetlag / late night**: When $|P|$ drifts beyond $\pm 6$h (half-cycle), fold semantics create sign ambiguity at $\pm 12$h. Valid control zone: $|P| \le 6$h. Beyond that: "uncertain phase", use sleep-window constraint, not light therapy.

### Conclusion
Under normal observation (main sleep exists) and moderate perturbation ($|P| \le 6$h), $\widehat{CBT}_{\min}$ reliably drives PRC-based control. Extreme cases degrade to safe mode (no light intervention).
