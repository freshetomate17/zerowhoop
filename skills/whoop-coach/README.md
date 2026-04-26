# whoop-coach

Reads structured findings from the database and delivers personalized, conversational health guidance via Discord or CLI. The user-facing layer of the ZeroWhoop pipeline.

## Install

Clone the ZeroWhoop repo and initialize the database:

```bash
git clone https://github.com/your-org/zerowhoop
sqlite3 ~/.zeroclaw/workspace/data/whoop.db < schema.sql
```

For Discord delivery, add your bot credentials to `~/.zeroclaw/config.toml`:

```toml
[discord]
bot_token = "..."
channel_id = "..."
```

## Permissions

| Permission | Why |
|---|---|
| `file_read` | Reads findings and message history from `whoop.db` |
| `file_write` | Marks findings as consumed, logs outgoing messages |
| `network` | Sends messages via the Discord API |

## Usage

### Morning briefing
```
coach_briefing(channel: str = "cli") -> str
```

Reads unconsumed findings, synthesizes them into 1-3 sentences of actionable guidance, and sends via the specified channel (`"cli"` or `"discord"`).

### Ad-hoc response
```
coach_respond(query: str, channel: str = "cli") -> str
```

Answers a specific question in context of the latest findings.

**Example trigger phrases:**
- "Should I train today?"
- "Give me my morning briefing"
- "What's going on with my recovery?"
- "How am I doing?"

## Deduplication

The coach tracks consumed findings and does not repeat the same finding within 24 hours unless severity escalates.

> ZeroWhoop is not medical advice. For health concerns, talk to a clinician.

## Part of ZeroWhoop

This skill is part of the [ZeroWhoop](https://github.com/your-org/zerowhoop) pipeline:
`whoop-ingest` → `whoop-interpret` → `whoop-coach`
