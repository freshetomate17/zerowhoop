#!/usr/bin/env python3
"""
whoop-ingest: fetch.py
Fetches WHOOP biometric data from the API and upserts into the shared SQLite DB.

Usage:
    python fetch.py --metric all --days 14
    python fetch.py --metric recovery --days 7
"""

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        sys.exit("tomllib not available. Python >=3.11 has it built-in, or: pip install tomli")

# SecretStore lives two levels up in lib/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "lib"))
from secret_store import SecretStore  # noqa: E402

CONFIG_PATH = Path.home() / ".zeroclaw" / "config.toml"
DB_PATH = Path.home() / ".zeroclaw" / "workspace" / "data" / "whoop.db"
WHOOP_BASE = "https://api.prod.whoop.com/developer/v1"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
MOCK_SEED_PATH = Path.home() / ".zeroclaw" / "workspace" / "data" / "mock_whoop_seed.json"

PLUGIN_NAME = "whoop"

SPORT_NAMES: dict[int, str] = {
    -1: "activity", 0: "running", 1: "cycling", 16: "baseball",
    17: "basketball", 18: "rowing", 19: "fencing", 20: "field hockey",
    21: "football", 22: "golf", 24: "ice hockey", 25: "lacrosse",
    27: "rugby", 28: "sailing", 29: "skiing", 30: "soccer",
    31: "softball", 32: "squash", 33: "swimming", 34: "tennis",
    35: "track and field", 36: "volleyball", 37: "water polo",
    38: "wrestling", 39: "boxing", 42: "dance", 43: "pilates",
    44: "yoga", 45: "weightlifting", 47: "cross country skiing",
    48: "functional fitness", 49: "duathlon", 51: "gymnastics",
    52: "hiking", 53: "horseback riding", 55: "kayaking",
    56: "martial arts", 57: "mountain biking", 59: "powerlifting",
    60: "rock climbing", 61: "paddleboarding", 62: "triathlon",
    63: "walking", 64: "surfing", 65: "elliptical", 66: "stairmaster",
    70: "meditation", 71: "other", 82: "ultimate", 84: "jumping rope",
    91: "snowboarding", 96: "hiit", 97: "spin", 98: "jiu jitsu",
    101: "pickleball", 107: "barre", 128: "stretching",
    230: "table tennis", 231: "badminton", 233: "sauna", 234: "disc golf",
}


# ---------------------------------------------------------------------------
# Config and secret helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """Load non-secret config (mode, channel_id, etc.) from config.toml."""
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def ensure_valid_token(store: SecretStore) -> str:
    """Return a valid access token, refreshing via OAuth if expired.

    Reads credentials from the SecretStore and writes refreshed tokens back
    to the SecretStore — never touches config.toml for secrets.
    """
    expires_str = store.get("whoop_token_expires_at")

    try:
        expires_at = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) < expires_at - timedelta(minutes=5):
            return store.get("whoop_access_token")
    except (ValueError, AttributeError):
        pass

    print("Access token expired or missing — refreshing...", file=sys.stderr)
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": store.get("whoop_refresh_token"),
            "client_id": store.get("whoop_client_id"),
            "client_secret": store.get("whoop_client_secret"),
        },
        timeout=15,
    )
    if resp.status_code != 200:
        sys.exit(
            f"Token refresh failed ({resp.status_code}). "
            "Re-authenticate at developer.whoop.com, then run:\n"
            "  python scripts/plugin_secrets.py set whoop whoop_access_token\n"
            "  python scripts/plugin_secrets.py set whoop whoop_refresh_token"
        )

    data = resp.json()
    new_access = data["access_token"]
    new_refresh = data.get("refresh_token", store.get("whoop_refresh_token"))
    expires_in = data.get("expires_in", 3600)
    new_expires = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Write refreshed tokens back to the SecretStore (encrypted)
    store.set("whoop_access_token", new_access)
    store.set("whoop_refresh_token", new_refresh)
    # token_expires_at is not sensitive; store plaintext for easy inspection
    store.set("whoop_token_expires_at", new_expires, encrypt=False)

    print(f"Token refreshed. Expiry: {new_expires}", file=sys.stderr)
    return new_access


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _date_range_params(days: int) -> dict:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return {
        "start": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "end": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    }


def _paginate(session: requests.Session, url: str, params: dict) -> list:
    """Collect all records from a cursor-paginated WHOOP endpoint."""
    records: list = []
    next_token = None

    while True:
        p = dict(params)
        if next_token:
            p["nextToken"] = next_token

        for attempt in range(4):
            resp = session.get(url, params=p, timeout=15)
            if resp.status_code == 429:
                wait = 2 ** attempt
                print(f"Rate limited — waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            break
        else:
            sys.exit(f"Failed to fetch {url} after retries (rate limited).")

        body = resp.json()
        records.extend(body.get("records", []))
        next_token = body.get("next_token")
        if not next_token:
            break

    return records


# ---------------------------------------------------------------------------
# Fetch functions
# ---------------------------------------------------------------------------

def fetch_recovery(session: requests.Session, days: int) -> list:
    return _paginate(session, f"{WHOOP_BASE}/recovery", _date_range_params(days))


def fetch_sleep(session: requests.Session, days: int) -> list:
    return _paginate(session, f"{WHOOP_BASE}/activity/sleep", _date_range_params(days))


def fetch_workouts(session: requests.Session, days: int) -> list:
    return _paginate(session, f"{WHOOP_BASE}/activity/workout", _date_range_params(days))


def fetch_cycles(session: requests.Session, days: int) -> list:
    return _paginate(session, f"{WHOOP_BASE}/cycle", _date_range_params(days))


# ---------------------------------------------------------------------------
# Write functions (idempotent via INSERT OR REPLACE)
# ---------------------------------------------------------------------------

def write_recovery(conn: sqlite3.Connection, records: list) -> tuple[int, int]:
    inserted = updated = 0
    for r in records:
        if r.get("score_state") != "SCORED":
            continue
        score = r.get("score", {})
        date = r["created_at"][:10]

        exists = conn.execute(
            "SELECT 1 FROM whoop_recovery WHERE date = ?", (date,)
        ).fetchone()

        conn.execute(
            """
            INSERT OR REPLACE INTO whoop_recovery
                (date, recovery_score, hrv_ms, resting_hr, skin_temp_c, spo2_pct, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                score.get("recovery_score"),
                score.get("hrv_rmssd_milli"),
                score.get("resting_heart_rate"),
                score.get("skin_temp_celsius"),
                score.get("spo2_percentage"),
                json.dumps(r),
            ),
        )
        if exists:
            updated += 1
        else:
            inserted += 1

    conn.commit()
    return inserted, updated


def write_sleep(conn: sqlite3.Connection, records: list) -> tuple[int, int]:
    inserted = updated = 0
    for r in records:
        if r.get("score_state") != "SCORED" or r.get("nap"):
            continue
        score = r.get("score", {})
        stage = score.get("stage_summary", {})
        needed = score.get("sleep_needed", {})
        date = r["start"][:10]

        total_sleep_min = (
            stage.get("total_light_sleep_time_milli", 0)
            + stage.get("total_slow_wave_sleep_time_milli", 0)
            + stage.get("total_rem_sleep_time_milli", 0)
        ) // 60000

        sleep_need_min = (
            needed.get("baseline_milli", 0)
            + needed.get("need_from_sleep_debt_milli", 0)
            + needed.get("need_from_recent_strain_milli", 0)
        ) // 60000

        efficiency_raw = score.get("sleep_efficiency_percentage")
        efficiency = efficiency_raw / 100.0 if efficiency_raw is not None else None

        exists = conn.execute(
            "SELECT 1 FROM whoop_sleep WHERE date = ?", (date,)
        ).fetchone()

        conn.execute(
            """
            INSERT OR REPLACE INTO whoop_sleep
                (date, total_sleep_min, sleep_efficiency, sleep_performance,
                 sleep_consistency, deep_min, rem_min, light_min, awake_min,
                 sleep_need_min, debt_min, bedtime, wake_time, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                total_sleep_min,
                efficiency,
                score.get("sleep_performance_percentage"),
                score.get("sleep_consistency_percentage"),
                stage.get("total_slow_wave_sleep_time_milli", 0) // 60000,
                stage.get("total_rem_sleep_time_milli", 0) // 60000,
                stage.get("total_light_sleep_time_milli", 0) // 60000,
                stage.get("total_awake_time_milli", 0) // 60000,
                sleep_need_min,
                None,  # debt_min: cumulative; computed by whoop-interpret, not per-record
                r.get("start"),
                r.get("end"),
                json.dumps(r),
            ),
        )
        if exists:
            updated += 1
        else:
            inserted += 1

    conn.commit()
    return inserted, updated


def write_workouts(conn: sqlite3.Connection, records: list) -> tuple[int, int]:
    inserted = updated = 0
    for r in records:
        if r.get("score_state") != "SCORED":
            continue
        score = r.get("score", {})
        date = r["start"][:10]
        sport = SPORT_NAMES.get(r.get("sport_id", -1), str(r.get("sport_id", "unknown")))

        duration_min = None
        if r.get("start") and r.get("end"):
            try:
                s = datetime.fromisoformat(r["start"].replace("Z", "+00:00"))
                e = datetime.fromisoformat(r["end"].replace("Z", "+00:00"))
                duration_min = int((e - s).total_seconds() // 60)
            except ValueError:
                pass

        workout_id = str(r["id"])
        exists = conn.execute(
            "SELECT 1 FROM whoop_workouts WHERE workout_id = ?", (workout_id,)
        ).fetchone()

        conn.execute(
            """
            INSERT OR REPLACE INTO whoop_workouts
                (workout_id, date, sport, strain, avg_hr, max_hr,
                 kj_burned, duration_min, start_time, end_time, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                workout_id,
                date,
                sport,
                score.get("strain"),
                score.get("average_heart_rate"),
                score.get("max_heart_rate"),
                score.get("kilojoule"),
                duration_min,
                r.get("start"),
                r.get("end"),
                json.dumps(r),
            ),
        )
        if exists:
            updated += 1
        else:
            inserted += 1

    conn.commit()
    return inserted, updated


def write_cycles(conn: sqlite3.Connection, records: list) -> tuple[int, int]:
    inserted = updated = 0
    for r in records:
        if r.get("score_state") != "SCORED":
            continue
        score = r.get("score", {})
        date = r["start"][:10]
        cycle_id = str(r["id"])

        exists = conn.execute(
            "SELECT 1 FROM whoop_cycles WHERE cycle_id = ?", (cycle_id,)
        ).fetchone()

        conn.execute(
            """
            INSERT OR REPLACE INTO whoop_cycles
                (cycle_id, date, day_strain, avg_hr, max_hr, kj_burned, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cycle_id,
                date,
                score.get("strain"),
                score.get("average_heart_rate"),
                score.get("max_heart_rate"),
                score.get("kilojoule"),
                json.dumps(r),
            ),
        )
        if exists:
            updated += 1
        else:
            inserted += 1

    conn.commit()
    return inserted, updated


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------

def load_mock(metric: str) -> list:
    if not MOCK_SEED_PATH.exists():
        sys.exit(
            f"Mock seed not found at {MOCK_SEED_PATH}. "
            "Run mock/generate_mock_data.py first."
        )
    with open(MOCK_SEED_PATH) as f:
        seed = json.load(f)
    return seed.get(metric, [])


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

FETCH_FNS = {
    "recovery": fetch_recovery,
    "sleep": fetch_sleep,
    "workouts": fetch_workouts,
    "cycles": fetch_cycles,
}
WRITE_FNS = {
    "recovery": write_recovery,
    "sleep": write_sleep,
    "workouts": write_workouts,
    "cycles": write_cycles,
}


def run_metric(
    metric: str,
    days: int,
    session: requests.Session | None,
    conn: sqlite3.Connection,
    mock: bool,
) -> dict:
    if mock:
        records = load_mock(metric)
    else:
        records = FETCH_FNS[metric](session, days)  # type: ignore[arg-type]

    inserted, updated = WRITE_FNS[metric](conn, records)

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return {
        "metric": metric,
        "rows_fetched": len(records),
        "rows_inserted": inserted,
        "rows_updated": updated,
        "date_range": [start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")],
        "source": "mock" if mock else "whoop",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch WHOOP biometric data into the shared SQLite database."
    )
    parser.add_argument(
        "--metric",
        default="all",
        choices=["all", "recovery", "sleep", "workouts", "cycles"],
        help="Which metric to fetch (default: all)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="How many days back to fetch (default: 7, max: 30)",
    )
    args = parser.parse_args()
    args.days = min(args.days, 30)

    cfg = load_config()
    mock = cfg.get("whoop", {}).get("mode") == "mock"

    if not DB_PATH.exists():
        sys.exit(
            f"Database not found at {DB_PATH}. "
            "Run: sqlite3 ~/.zeroclaw/workspace/data/whoop.db < schema.sql"
        )

    conn = sqlite3.connect(DB_PATH)

    if mock:
        session = None
        print("Running in mock mode.", file=sys.stderr)
    else:
        store = SecretStore(PLUGIN_NAME)
        token = ensure_valid_token(store)
        session = requests.Session()
        session.headers["Authorization"] = f"Bearer {token}"

    metrics = (
        ["recovery", "sleep", "workouts", "cycles"]
        if args.metric == "all"
        else [args.metric]
    )

    for m in metrics:
        result = run_metric(m, args.days, session, conn, mock)
        print(json.dumps(result))

    conn.close()


if __name__ == "__main__":
    main()
