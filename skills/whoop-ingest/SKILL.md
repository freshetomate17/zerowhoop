---
name: whoop-ingest
description: Fetches biometric data from the WHOOP API (sleep, recovery, strain, workouts, cycles) and stores it in the local SQLite database. Use this skill whenever the agent needs fresh WHOOP data, when the user asks about their recent sleep/recovery/strain, or when other skills request biometric data via the database. Triggers on phrases like "fetch my whoop data", "sync my recovery", "get latest sleep", or as a prerequisite for analysis tasks.
license: MIT
---

# whoop-ingest

Fetches WHOOP biometric data via the official WHOOP API v1 and stores it in the shared `whoop.db` SQLite database.

## When to use

Use this skill when:
- Fresh data needs to be pulled from WHOOP before any analysis
- The user asks about recent sleep, recovery, strain or workouts
- Another skill needs current biometric context
- Scheduled morning sync is triggered

Do NOT use this skill for analysis or interpretation — that is `whoop-interpret`.
Do NOT use this skill for sending messages — that is `whoop-coach`.

## How to use

The skill exposes a single primary tool:

```
whoop_fetch(metric: str, days: int = 7) -> dict
```

**Parameters:**
- `metric`: one of `recovery`, `sleep`, `workouts`, `cycles`, or `all`
- `days`: how many days back to fetch (default 7, max 30)

**Returns:**
```json
{
  "metric": "recovery",
  "rows_fetched": 7,
  "rows_inserted": 5,
  "rows_updated": 2,
  "date_range": ["2026-04-19", "2026-04-26"],
  "source": "whoop"
}
```

The skill writes data directly to the database tables defined in `schema.sql`:
- `whoop_recovery`, `whoop_sleep`, `whoop_workouts`, `whoop_cycles`

Other skills should read from those tables, not call this skill's tools directly.

## Authentication

The skill reads OAuth tokens from `~/.zeroclaw/config.toml`:

```toml
[whoop]
access_token = "..."
refresh_token = "..."
client_id = "..."
client_secret = "..."
token_expires_at = "2026-04-26T20:00:00Z"
```

If the access token is expired, the skill attempts a refresh using the refresh token. If refresh fails, the skill returns a clear error and asks the user to re-authenticate at `developer.whoop.com`.

## Mock mode

For development without a live WHOOP account, set:

```toml
[whoop]
mode = "mock"
```

In mock mode, the skill reads from `~/.zeroclaw/workspace/data/mock_whoop_seed.json` instead of calling the API. Use `mock/generate_mock_data.py` to generate this seed.

## Agent invocation

When this skill is needed, invoke the script directly via shell:

```bash
# Fetch all metrics for the last 7 days (default)
python skills/whoop-ingest/fetch.py --metric all --days 7

# Fetch only recovery for the last 14 days
python skills/whoop-ingest/fetch.py --metric recovery --days 14

# Full sync before a deep analysis
python skills/whoop-ingest/fetch.py --metric all --days 30
```

Each metric prints one JSON result to stdout:
```json
{"metric": "recovery", "rows_fetched": 7, "rows_inserted": 5, "rows_updated": 2, "date_range": ["2026-04-19", "2026-04-26"], "source": "whoop"}
```

If `rows_fetched` is 0, the WHOOP account may have no data for that window or the token may need re-authentication.

## Dependencies

```
requests>=2.28
tomli>=2.0    # only needed on Python < 3.11; tomllib is built-in from 3.11+
```

Install with: `pip install requests tomli`

## Implementation notes

- Python script `fetch.py` invoked via the agent's shell
- Uses `requests` for the WHOOP API with cursor-based pagination (`nextToken`)
- Uses `sqlite3` (stdlib) for all database writes
- Idempotent: checks row existence before each write; same date/id upserts, never duplicates
- Skips `nap` records from the sleep table (main sleep only)
- Only writes records with `score_state == "SCORED"`; pending/unscored records are skipped

API endpoints used:
- `GET /developer/v1/recovery` — recovery scores
- `GET /developer/v1/activity/sleep` — sleep data
- `GET /developer/v1/activity/workout` — workouts
- `GET /developer/v1/cycle` — daily cycles

Rate limits: 100 requests per minute. The skill retries with exponential backoff on 429.

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Token expired | Skill attempts refresh; if fails, user re-auths |
| `403 Forbidden` | Insufficient scope | Re-auth with `read:recovery read:sleep read:workout read:cycles` |
| `429 Rate Limited` | Too many calls | Skill backs off automatically |
| `Database is locked` | Concurrent write | Skill retries 3x with backoff |

## Output schema for downstream skills

After running, downstream skills can query:

```sql
SELECT * FROM whoop_recovery WHERE date >= date('now', '-7 days');
SELECT * FROM whoop_sleep WHERE date >= date('now', '-7 days');
SELECT * FROM whoop_workouts WHERE date >= date('now', '-7 days');
```

See `schema.sql` for full column definitions.
