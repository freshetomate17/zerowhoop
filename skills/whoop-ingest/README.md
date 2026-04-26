# whoop-ingest

Fetches biometric data from the WHOOP API (sleep, recovery, strain, workouts, cycles) and stores it in the local SQLite database. The first step in the ZeroWhoop pipeline — run this before `whoop-interpret` or `whoop-coach`.

## Install

Clone the ZeroWhoop repo and initialize the database:

```bash
git clone https://github.com/your-org/zerowhoop
sqlite3 ~/.zeroclaw/workspace/data/whoop.db < schema.sql
```

## Permissions

| Permission | Why |
|---|---|
| `network` | Calls the WHOOP API v1 endpoints |
| `file_read` | Reads OAuth tokens from `~/.zeroclaw/config.toml` |
| `file_write` | Writes fetched data to `whoop.db` |

## Configuration

Add your WHOOP credentials to `~/.zeroclaw/config.toml`:

```toml
[whoop]
access_token = "..."
refresh_token = "..."
client_id = "..."
client_secret = "..."
token_expires_at = "2026-04-26T20:00:00Z"
```

Get credentials at [developer.whoop.com](https://developer.whoop.com). Required scopes: `read:recovery read:sleep read:workout read:cycles`.

## Usage

```
whoop_fetch(metric: str, days: int = 7) -> dict
```

- `metric`: `recovery`, `sleep`, `workouts`, `cycles`, or `all`
- `days`: how many days back to fetch (default 7, max 30)

**Example trigger phrases:**
- "Fetch my WHOOP data"
- "Sync my recovery"
- "Get my latest sleep"

## Mock mode

For development without a live WHOOP account:

```toml
[whoop]
mode = "mock"
```

Generate mock data with `mock/generate_mock_data.py`.

## Part of ZeroWhoop

This skill is part of the [ZeroWhoop](https://github.com/your-org/zerowhoop) pipeline:
`whoop-ingest` → `whoop-interpret` → `whoop-coach`
