---
name: whoop-interpret
description: Analyzes stored WHOOP data to detect health-relevant patterns including HRV trends, sleep debt accumulation, strain-recovery mismatches, elevated resting heart rate, and workout-sleep correlations. Writes structured findings with clinical framing to the findings table. Use this skill when the agent needs to understand what the data means, when the user asks "how am I doing", "any patterns", "what's going on", or as the analysis step between ingest and coach. Outputs are findings, not recommendations — recommendations are the coach's job.
license: MIT
---

# whoop-interpret

Reads WHOOP data from the shared database, detects clinically-meaningful patterns, and writes structured findings.

## When to use

Use this skill when:
- The user asks about their health status, trends or patterns
- A morning briefing is being prepared and needs underlying findings
- After `whoop-ingest` has fetched fresh data
- The user asks "what's going on" or "how am I doing"

Do NOT use this skill for raw data fetching — that is `whoop-ingest`.
Do NOT use this skill to send messages or recommendations — that is `whoop-coach`.

## What this skill does — and does not — produce

This skill produces **findings**, not recommendations. The distinction is important and clinical:

- A **finding** describes what is happening: *"HRV has dropped 18% over 7 days while strain is unchanged."*
- A **recommendation** prescribes what to do: *"Reduce training volume tomorrow."*

Recommendations are `whoop-coach`'s job. Keeping these separate makes the system clinically defensible and lets findings be reused across multiple coaching styles.

## How to use

The skill exposes one primary tool:

```
whoop_interpret(window_days: int = 14) -> list[finding]
```

**Returns:** a list of finding dicts, also written to the `findings` table.

```json
{
  "id": 42,
  "pattern_type": "hrv_downtrend",
  "severity": "med",
  "confidence": 0.78,
  "window_days": 7,
  "finding_text": "HRV has trended downward over the past 5 days, dropping from 72ms to 58ms (-19%). This pattern persists despite stable sleep duration.",
  "evidence_json": {
    "hrv_series": [72, 69, 65, 62, 58],
    "dates": ["2026-04-22", "..."],
    "slope_ms_per_day": -3.5,
    "p_value": 0.04
  },
  "suggested_action": "consider_lower_intensity_training"
}
```

## Patterns detected (v1)

Each pattern is a self-contained detector. Add new ones by extending the detector list.

### 1. `hrv_downtrend`
**Trigger:** Linear regression on last N days of HRV shows negative slope with p < 0.1 and >10% drop.
**Severity:** `low` if 10-15% drop, `med` if 15-25%, `high` if >25%.

### 2. `sleep_debt`
**Trigger:** Cumulative sleep debt (sleep_need_min - total_sleep_min summed) exceeds 4 hours over 7 days.
**Severity:** `low` <4h, `med` 4-8h, `high` >8h.

### 3. `strain_recovery_mismatch`
**Trigger:** Average strain in past 3 days > 14 while average recovery score < 50.
**Severity:** `low` if 1 day, `med` if 2 days, `high` if 3+ days.

### 4. `elevated_rhr`
**Trigger:** Resting HR is >5 bpm above 30-day baseline for 3+ consecutive days.
**Severity:** Based on absolute deviation from baseline.

### 5. `workout_sleep_correlation`
**Trigger:** Within last 14 days, workouts ending after 19:00 correlate with sleep efficiency drop >10% versus baseline.
**Severity:** Based on correlation strength.

## Clinical reference values

The skill reads `reference_values.md` (in this skill's directory) for normative ranges. Reference values are conservative and based on published literature. They are **not patient-specific** — that is a hard constraint of an unsupervised health tool.

## Output discipline

Each finding written to the database must include:
- `pattern_type` from the fixed vocabulary above
- `severity` ∈ {low, med, high}
- `confidence` ∈ [0, 1]
- `evidence_json` with the actual data the finding is based on
- `finding_text` — one or two sentences in plain language

Findings without evidence are not written. If a pattern threshold is not met, the skill writes nothing rather than a "no finding" placeholder.

## Implementation notes

- Implemented as a Python script using `pandas`, `numpy`, `scipy.stats`
- Reads from `whoop_recovery`, `whoop_sleep`, `whoop_workouts`, `whoop_cycles`
- Writes to `findings` (one row per detected pattern)
- Idempotent within a calendar day: re-running on the same data updates rather than duplicates findings of the same `pattern_type` for the same evidence window
- All findings include a `confidence` score; coach skill should down-weight low-confidence findings

## Disclaimer (must be included in any user-facing output)

ZeroWhoop findings are not medical advice. They are pattern detections on consumer wearable data, with all the limitations that implies. Always consult a healthcare professional for medical decisions.
