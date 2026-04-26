# ZeroWhoop

Three composable [ZeroClaw](https://github.com/zeroclaw-labs/zeroclaw) skills that turn raw WHOOP data into personalized health guidance.

> Built at Sundai Hackathon, April 2026.

## What it does

ZeroWhoop is a pipeline of three skills that work together:

1. **`whoop-ingest`** — Fetches sleep, recovery, strain and workout data from the WHOOP API and stores it locally.
2. **`whoop-interpret`** — Detects health patterns (HRV trends, sleep debt, strain-recovery mismatch) and writes clinically-framed findings.
3. **`whoop-coach`** — Generates personalized briefings and recommendations, delivered via Discord.

Skills communicate through a shared SQLite database. Each skill is independently usable.

## Architecture

```
WHOOP API ──▶ whoop-ingest ──▶ SQLite ──▶ whoop-interpret ──▶ findings ──▶ whoop-coach ──▶ Discord
                                                                                             │
                                                              Calendar (MCP) ◀───────────────┘
```

## Quick start

```bash
# Install ZeroClaw (if not already installed)
curl -fsSL https://raw.githubusercontent.com/zeroclaw-labs/zeroclaw/master/install.sh | bash
zeroclaw onboard

# Clone this repo
git clone https://github.com/<your-username>/zerowhoop.git
cd zerowhoop

# Install the schema
sqlite3 ~/.zeroclaw/workspace/data/whoop.db < schema.sql

# Install the skills
zeroclaw skills install ./skills/whoop-ingest
zeroclaw skills install ./skills/whoop-interpret
zeroclaw skills install ./skills/whoop-coach

# Verify
zeroclaw skills list
```

## Configuration

Add to `~/.zeroclaw/config.toml`:

```toml
[whoop]
access_token = "your-whoop-oauth-token"
refresh_token = "your-refresh-token"

[discord]
bot_token = "your-discord-bot-token"
channel_id = "your-channel-id"
```

## Mock mode

For development without a live WHOOP account:

```bash
python mock/generate_mock_data.py --days 30
```

This populates the database with realistic synthetic data including the patterns the interpret skill detects.

## Project structure

```
zerowhoop/
├── README.md                    # this file
├── LICENSE                      # MIT
├── schema.sql                   # locked SQLite schema (the contract)
├── mock/
│   └── generate_mock_data.py    # synthetic data generator
├── skills/
│   ├── whoop-ingest/
│   │   └── SKILL.md
│   ├── whoop-interpret/
│   │   ├── SKILL.md
│   │   └── reference_values.md  # clinical reference data
│   └── whoop-coach/
│       └── SKILL.md
└── LICENSE```

## Disclaimer

ZeroWhoop is not medical advice. The findings and suggestions it generates are for informational purposes only. Always consult a qualified healthcare professional for medical decisions.

## License

MIT — see `LICENSE`.
