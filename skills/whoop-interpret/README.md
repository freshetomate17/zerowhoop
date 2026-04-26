# whoop-interpret

Analyzes stored WHOOP data to detect clinically-meaningful patterns: HRV trends, sleep debt, strain-recovery mismatches, elevated resting heart rate, and late-workout/sleep correlations. Writes structured findings to the database for `whoop-coach` to act on.

## Install

Clone the ZeroWhoop repo and initialize the database:

```bash
git clone https://github.com/your-org/zerowhoop
sqlite3 ~/.zeroclaw/workspace/data/whoop.db < schema.sql
```

Requires `whoop-ingest` to have populated data first.

## Permissions

| Permission | Why |
|---|---|
| `file_read` | Reads WHOOP data from `whoop.db` |
| `file_write` | Writes detected findings to `whoop.db` |

## Usage

```
whoop_interpret(window_days: int = 14) -> list[finding]
```

- `window_days`: analysis window in days (default 14)

**Example trigger phrases:**
- "How am I doing?"
- "Any patterns in my data?"
- "What's going on with my HRV?"

## Patterns detected

| Pattern | Trigger |
|---|---|
| `hrv_downtrend` | HRV drops >10% over 7+ days (linear regression, p < 0.1) |
| `sleep_debt` | Cumulative sleep deficit >4 hours over 7 days |
| `strain_recovery_mismatch` | Avg strain >14 with avg recovery <50 for 3+ days |
| `elevated_rhr` | Resting HR >5 bpm above 30-day baseline for 3+ days |
| `workout_sleep_correlation` | Late workouts (after 19:00) correlated with sleep efficiency drop >10% |

Every finding includes a `confidence` score and `evidence_json` with the raw data it's based on.

> ZeroWhoop findings are not medical advice. Always consult a healthcare professional for medical decisions.

## Part of ZeroWhoop

This skill is part of the [ZeroWhoop](https://github.com/your-org/zerowhoop) pipeline:
`whoop-ingest` → `whoop-interpret` → `whoop-coach`
