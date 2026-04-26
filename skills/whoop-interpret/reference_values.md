# Clinical reference values for whoop-interpret

These are conservative, population-level reference ranges drawn from published literature.
They are **not** patient-specific. Always personalize against the individual's own baseline
where possible (using their first 14-30 days as a personal reference).

## Heart Rate Variability (HRV, RMSSD-derived, ms)

WHOOP reports HRV as RMSSD (root mean square of successive differences), measured during slow-wave sleep.

| Age range | Typical range (ms) | Sources |
|---|---|---|
| 20-29 | 50-100 | Shaffer & Ginsberg, 2017 |
| 30-39 | 40-90 | Shaffer & Ginsberg, 2017 |
| 40-49 | 35-75 | Shaffer & Ginsberg, 2017 |
| 50-59 | 25-65 | Shaffer & Ginsberg, 2017 |
| 60+ | 20-55 | Shaffer & Ginsberg, 2017 |

**Important:** Within-person variability matters more than population averages.
A 20% drop from individual baseline is more meaningful than an absolute number.

## Resting Heart Rate (RHR, bpm)

| Category | Range |
|---|---|
| Athlete | 40-60 |
| Excellent fitness | 50-65 |
| Good | 60-70 |
| Average | 70-80 |
| Above average | 80-90 |
| Concerning | >90 (in rest, sustained) |

**Trend matters:** A 5+ bpm increase over personal baseline for 3+ consecutive days
warrants attention (often precedes illness onset by 24-48h).

## Sleep duration (adults 18-64)

| Recommendation | Hours |
|---|---|
| Recommended (NSF) | 7-9 |
| May be appropriate | 6-7 or 9-10 |
| Not recommended | <6 or >10 |

Source: National Sleep Foundation, Hirshkowitz et al., 2015.

## Sleep architecture (% of total sleep time)

| Stage | Typical % |
|---|---|
| Deep (slow-wave) | 13-23% |
| REM | 20-25% |
| Light | 50-60% |
| Awake | <5% |

Wearable estimates of sleep stages have known accuracy limitations
(Beattie et al., 2017; de Zambotti et al., 2019). Use as trend indicators,
not absolute measurements.

## Sleep efficiency

Total sleep time / time in bed.

| Category | Range |
|---|---|
| Excellent | >90% |
| Good | 85-90% |
| Acceptable | 75-85% |
| Poor | <75% |

## Strain (WHOOP-specific scale)

WHOOP strain is on a 0-21 scale based on cardiovascular load.

| Category | Range |
|---|---|
| All day rest | 0-9 |
| Light | 10-13 |
| Moderate | 14-17 |
| Strenuous | 18-21 |

## Recovery score (WHOOP-specific)

| Category | Range |
|---|---|
| Green (recovered) | 67-100 |
| Yellow (moderate) | 34-66 |
| Red (low) | 0-33 |

## Strain-recovery mismatch threshold

A practical heuristic from sports science:
- High strain (>14) sustained while recovery is low (<50) for 3+ days
  predicts elevated injury risk and overreaching.

## Skin temperature deviation

| Deviation from baseline | Interpretation |
|---|---|
| <0.5°C | Normal variation |
| 0.5-1.0°C | Worth monitoring |
| >1.0°C sustained | May precede illness; non-specific |

Note: Skin temp is influenced by environment, menstrual cycle, and many factors.
Treat as one signal among many, not diagnostic.

## What this skill does NOT use

- Single-day spikes in any metric (too noisy)
- Cross-comparisons between users (every body is different)
- Diagnosis of any medical condition
- Estimates of fitness gains or losses
- Predictions of specific health events

## References (for the SKILL.md author, not for output)

- Shaffer F, Ginsberg JP. An Overview of Heart Rate Variability Metrics and Norms. Front Public Health. 2017;5:258.
- Hirshkowitz M, et al. National Sleep Foundation's sleep time duration recommendations. Sleep Health. 2015;1(1):40-43.
- Beattie Z, et al. Estimation of sleep stages in a healthy adult population from optical plethysmography and accelerometer signals. Physiol Meas. 2017;38(11):1968-1979.
- de Zambotti M, et al. Wearable Sleep Technology in Clinical and Research Settings. Med Sci Sports Exerc. 2019;51(7):1538-1557.
