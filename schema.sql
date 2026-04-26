-- ZeroWhoop shared SQLite schema
-- This file is the contract between all three skills.
-- DO NOT change column names without updating all skills + mock generator.
--
-- Database location: ~/.zeroclaw/workspace/data/whoop.db
-- Install with: sqlite3 ~/.zeroclaw/workspace/data/whoop.db < schema.sql

-- ============================================================================
-- RAW WHOOP DATA (written by whoop-ingest, read by whoop-interpret)
-- ============================================================================

-- Daily recovery metrics
CREATE TABLE IF NOT EXISTS whoop_recovery (
    date            TEXT PRIMARY KEY,         -- ISO date YYYY-MM-DD
    recovery_score  INTEGER,                  -- 0-100
    hrv_ms          REAL,                     -- heart rate variability in ms
    resting_hr      INTEGER,                  -- beats per minute
    skin_temp_c     REAL,                     -- skin temperature deviation
    spo2_pct        REAL,                     -- blood oxygen
    raw_json        TEXT,                     -- full WHOOP API response
    fetched_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Daily sleep summary
CREATE TABLE IF NOT EXISTS whoop_sleep (
    date                TEXT PRIMARY KEY,
    total_sleep_min     INTEGER,
    sleep_efficiency    REAL,                 -- 0.0-1.0
    sleep_performance   INTEGER,              -- 0-100, WHOOP's score
    sleep_consistency   INTEGER,              -- 0-100
    deep_min            INTEGER,
    rem_min             INTEGER,
    light_min           INTEGER,
    awake_min           INTEGER,
    sleep_need_min      INTEGER,              -- WHOOP's recommended sleep
    debt_min            INTEGER,              -- accumulated sleep debt
    bedtime             TEXT,                 -- ISO datetime
    wake_time           TEXT,                 -- ISO datetime
    raw_json            TEXT,
    fetched_at          TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Workout records
CREATE TABLE IF NOT EXISTS whoop_workouts (
    workout_id      TEXT PRIMARY KEY,
    date            TEXT NOT NULL,
    sport           TEXT,                     -- "running", "weightlifting", etc.
    strain          REAL,                     -- 0.0-21.0 WHOOP strain
    avg_hr          INTEGER,
    max_hr          INTEGER,
    kj_burned       REAL,
    duration_min    INTEGER,
    start_time      TEXT,                     -- ISO datetime
    end_time        TEXT,
    raw_json        TEXT,
    fetched_at      TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_workouts_date ON whoop_workouts(date);

-- Daily cycle (24h period in WHOOP terminology)
CREATE TABLE IF NOT EXISTS whoop_cycles (
    cycle_id        TEXT PRIMARY KEY,
    date            TEXT NOT NULL,
    day_strain      REAL,                     -- aggregate strain for the day
    avg_hr          INTEGER,
    max_hr          INTEGER,
    kj_burned       REAL,
    raw_json        TEXT,
    fetched_at      TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cycles_date ON whoop_cycles(date);

-- ============================================================================
-- DERIVED FINDINGS (written by whoop-interpret, read by whoop-coach)
-- ============================================================================

CREATE TABLE IF NOT EXISTS findings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           TEXT DEFAULT CURRENT_TIMESTAMP,
    pattern_type        TEXT NOT NULL,        -- "hrv_downtrend", "sleep_debt",
                                              -- "strain_recovery_mismatch",
                                              -- "workout_sleep_correlation",
                                              -- "elevated_rhr", etc.
    severity            TEXT NOT NULL,        -- "low" | "med" | "high"
    confidence          REAL,                 -- 0.0-1.0
    window_days         INTEGER,              -- analysis window used
    evidence_json       TEXT,                 -- structured supporting data
    finding_text        TEXT NOT NULL,        -- human-readable finding
    suggested_action    TEXT,                 -- proposed action for coach
    source_skill        TEXT DEFAULT 'whoop-interpret',
    consumed_at         TEXT,                 -- when coach used this finding
    consumed_by         TEXT                  -- which channel consumed it
);
CREATE INDEX IF NOT EXISTS idx_findings_timestamp ON findings(timestamp);
CREATE INDEX IF NOT EXISTS idx_findings_unconsumed ON findings(consumed_at) WHERE consumed_at IS NULL;

-- ============================================================================
-- COACH STATE (written and read by whoop-coach)
-- ============================================================================

-- Track what was said to whom, to avoid repetition
CREATE TABLE IF NOT EXISTS coach_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT DEFAULT CURRENT_TIMESTAMP,
    channel         TEXT,                     -- "discord", "cli"
    trigger         TEXT,                     -- "morning_briefing", "user_query"
    finding_id      INTEGER REFERENCES findings(id),
    message_text    TEXT NOT NULL,
    user_response   TEXT                      -- if user replied
);

-- ============================================================================
-- SCHEMA VERSION (for future migrations)
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    note        TEXT
);
INSERT OR IGNORE INTO schema_version (version, note) VALUES (1, 'initial schema');
