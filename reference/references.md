# MRDM References
This directory indexes literature that informs MRDM model decisions.

## Sleep Debt Recovery (S2)

| Reference | Key Insight | Impact on MRDM |
|---|---|---|
| Van Dongen et al. (2003) | Chronic restriction deficits equal total deprivation | Proportional recovery preferred |
| Banks and Dinges (2010) | One or two recovery nights insufficient | Motivates multi-night modeling; does not identify k=0.4 |
| Yamazaki et al. (2021) | Single recovery sleep insufficient | Fractional per-night decay |
| [Ochab et al. (2021)](https://doi.org/10.1371/journal.pone.0255771) | Recovery differs by outcome | Does not establish the MRDM debt equation |

## Regularity and interpretation

| Reference | Use in MRDM | Boundary |
|---|---|---|
| [Phillips et al. (2017)](https://doi.org/10.1038/s41598-017-03171-4) | Distinguish regularity from duration and timing | Wake-only consistency is not SRI |
| [Fischer, Klerman & Phillips (2021)](https://doi.org/10.1093/sleep/zsab103) | Choose metrics by sampling and question; report valid observations | No single metric describes every sleep pattern |
| [Murray et al. (2019)](https://pubmed.ncbi.nlm.nih.gov/31132578/) | Interpret timing relative to circadian phase in DSWPD | Does not imply earlier clock time is always better |

Visualization references and implementation choices: `docs/dev/rhythm_observation_and_3d.md`.

## v1.1 homeostatic-pressure scenarios

- [Borbély et al. (2016), The two-process model of sleep regulation: a reappraisal](https://doi.org/10.1111/jsr.12371): homeostatic regulation is distinct from circadian modulation; supports the Process S model family, not individual calibration.
- [Systematic individual differences in sleep homeostatic and circadian rhythm contributions to neurobehavioral impairment during sleep deprivation](https://pmc.ncbi.nlm.nih.gov/articles/PMC3260461/): reference rise/fall time constants and individual variability.
- [Banks et al. (2010), Neurobehavioral dynamics following chronic sleep restriction](https://pubmed.ncbi.nlm.nih.gov/20815182/): different neurobehavioral outcomes need not fully recover after one extended night.
- [Van Dongen et al. (2003)](https://pubmed.ncbi.nlm.nih.gov/12683469/): subjective sleepiness, sleep physiology and cognitive performance must not be treated as one interchangeable quantity.

The default model no longer treats cumulative D as sleep owed; the earlier S2 table describes the retired model. See `docs/dev/sleep_pressure_revision.md`.
