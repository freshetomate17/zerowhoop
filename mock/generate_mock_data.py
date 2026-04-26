#!/usr/bin/env python3
"""
Mock WHOOP data generator for ZeroWhoop development.

Generates 30 days of realistic synthetic data and writes it to the
shared SQLite database. The data deliberately includes the patterns
that whoop-interpret is designed to detect, so the demo has things
to find.

Usage:
    python mock/generate_mock_data.py --days 30
    python mock/generate_mock_data.py --days 30 --db /custom/path/whoop.db
    python mock/generate_mock_data.py --days 30 --reset  # clears existing rows first
"""
import argparse
import json
import os
import random
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


DEFAULT_DB = Path.home() / ".zeroclaw" / "workspace" / "data" / "whoop.db"


def daterange(end_date: datetime, days: int):
    """Yield dates from end_date going back `days` days, oldest first."""
    for i in range(days - 1, -1, -1):
        yield end_date - timedelta(days=i)


def gen_recovery(date: datetime, day_index: int, total_days: int) -> dict:
    """
    Generate a recovery record. Includes a deliberate HRV downtrend
    and elevated RHR pattern in the last 7 days.
    """
    # Baseline values
    baseline_hrv = 65
    baseline_rhr = 58

    # Last 7 days: HRV downtrend + elevated RHR
    days_from_end = total_days - 1 - day_index
    if days_from_end < 7:
        # Linear drift downward + noise
        drift = (7 - days_from_end) * -2.5
        hrv = baseline_hrv + drift + random.gauss(0, 3)
        rhr = baseline_rhr + (7 - days_from_end) * 0.8 + random.gauss(0, 1.5)
    else:
        hrv = baseline_hrv + random.gauss(0, 4)
        rhr = baseline_rhr + random.gauss(0, 2)

    hrv = max(20, min(100, hrv))
    rhr = max(45, min(85, rhr))

    # Recovery score: lower when HRV is low
    if hrv < 50:
        recovery = random.randint(20, 50)
    elif hrv < 65:
        recovery = random.randint(45, 70)
    else:
        recovery = random.randint(60, 90)

    return {
        "date": date.strftime("%Y-%m-%d"),
        "recovery_score": recovery,
        "hrv_ms": round(hrv, 1),
        "resting_hr": int(rhr),
        "skin_temp_c": round(random.gauss(0, 0.3), 2),
        "spo2_pct": round(random.gauss(97, 0.8), 1),
        "raw_json": json.dumps({"mock": True, "date": date.isoformat()}),
    }


def gen_sleep(date: datetime, day_index: int, total_days: int) -> dict:
    """
    Generate a sleep record. Includes deliberate sleep debt accumulation
    in days 10-20 and bad-sleep-after-late-workouts pattern.
    """
    sleep_need = 480  # 8 hours

    days_from_end = total_days - 1 - day_index

    # Sleep debt block: days 10-20 of the window have shorter sleep
    if 10 <= days_from_end <= 20:
        total_min = random.randint(360, 420)  # 6-7h
        efficiency = random.uniform(0.78, 0.86)
    # Late-workout-then-bad-sleep correlation: every 4th day
    elif day_index % 4 == 0 and days_from_end > 7:
        total_min = random.randint(380, 440)
        efficiency = random.uniform(0.72, 0.82)
    else:
        total_min = random.randint(420, 510)
        efficiency = random.uniform(0.85, 0.94)

    deep = int(total_min * random.uniform(0.13, 0.20))
    rem = int(total_min * random.uniform(0.18, 0.24))
    light = total_min - deep - rem
    awake = int(total_min * (1 - efficiency) / efficiency)

    bedtime = date.replace(hour=23, minute=random.randint(0, 59))
    wake_time = bedtime + timedelta(minutes=total_min + awake)

    return {
        "date": date.strftime("%Y-%m-%d"),
        "total_sleep_min": total_min,
        "sleep_efficiency": round(efficiency, 3),
        "sleep_performance": int(min(100, (total_min / sleep_need) * 100)),
        "sleep_consistency": random.randint(65, 90),
        "deep_min": deep,
        "rem_min": rem,
        "light_min": light,
        "awake_min": awake,
        "sleep_need_min": sleep_need,
        "debt_min": max(0, sleep_need - total_min),
        "bedtime": bedtime.isoformat(),
        "wake_time": wake_time.isoformat(),
        "raw_json": json.dumps({"mock": True, "date": date.isoformat()}),
    }


def gen_workouts(date: datetime, day_index: int, total_days: int) -> list:
    """
    Generate workouts. ~70% of days have a workout. Every 4th day has a LATE workout
    (after 19:00) to feed the workout-sleep correlation pattern.
    """
    if random.random() > 0.7:
        return []

    sports = ["running", "weightlifting", "cycling", "yoga", "rowing", "hiit"]
    sport = random.choice(sports)

    days_from_end = total_days - 1 - day_index

    # Late workout pattern
    if day_index % 4 == 0 and days_from_end > 7:
        start_hour = random.randint(19, 21)
    else:
        start_hour = random.choice([6, 7, 8, 12, 17, 18])

    duration = random.randint(30, 90)
    start_time = date.replace(hour=start_hour, minute=random.randint(0, 59))
    end_time = start_time + timedelta(minutes=duration)

    # Strain depends on sport + duration
    base_strain = {"running": 13, "weightlifting": 10, "cycling": 12,
                   "yoga": 6, "rowing": 14, "hiit": 16}.get(sport, 10)
    strain = base_strain + random.gauss(0, 1.5)
    strain = max(3, min(20, strain))

    avg_hr = random.randint(120, 165)
    max_hr = avg_hr + random.randint(15, 35)

    return [{
        "workout_id": str(uuid.uuid4()),
        "date": date.strftime("%Y-%m-%d"),
        "sport": sport,
        "strain": round(strain, 1),
        "avg_hr": avg_hr,
        "max_hr": max_hr,
        "kj_burned": round(duration * random.uniform(8, 15), 0),
        "duration_min": duration,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "raw_json": json.dumps({"mock": True}),
    }]


def gen_cycle(date: datetime, day_workouts: list) -> dict:
    """Generate a daily cycle aggregating workouts."""
    total_strain = sum(w["strain"] for w in day_workouts) if day_workouts else 0
    # Add baseline daily strain
    day_strain = total_strain + random.uniform(4, 8)
    day_strain = min(21, day_strain)

    return {
        "cycle_id": str(uuid.uuid4()),
        "date": date.strftime("%Y-%m-%d"),
        "day_strain": round(day_strain, 1),
        "avg_hr": random.randint(70, 95),
        "max_hr": max([w["max_hr"] for w in day_workouts], default=120),
        "kj_burned": round(sum(w.get("kj_burned", 0) for w in day_workouts) +
                          random.uniform(6000, 9000), 0),
        "raw_json": json.dumps({"mock": True}),
    }


def insert_recovery(conn: sqlite3.Connection, row: dict):
    conn.execute("""
        INSERT OR REPLACE INTO whoop_recovery
        (date, recovery_score, hrv_ms, resting_hr, skin_temp_c, spo2_pct, raw_json)
        VALUES (:date, :recovery_score, :hrv_ms, :resting_hr, :skin_temp_c, :spo2_pct, :raw_json)
    """, row)


def insert_sleep(conn: sqlite3.Connection, row: dict):
    conn.execute("""
        INSERT OR REPLACE INTO whoop_sleep
        (date, total_sleep_min, sleep_efficiency, sleep_performance, sleep_consistency,
         deep_min, rem_min, light_min, awake_min, sleep_need_min, debt_min,
         bedtime, wake_time, raw_json)
        VALUES (:date, :total_sleep_min, :sleep_efficiency, :sleep_performance, :sleep_consistency,
                :deep_min, :rem_min, :light_min, :awake_min, :sleep_need_min, :debt_min,
                :bedtime, :wake_time, :raw_json)
    """, row)


def insert_workout(conn: sqlite3.Connection, row: dict):
    conn.execute("""
        INSERT OR REPLACE INTO whoop_workouts
        (workout_id, date, sport, strain, avg_hr, max_hr, kj_burned, duration_min,
         start_time, end_time, raw_json)
        VALUES (:workout_id, :date, :sport, :strain, :avg_hr, :max_hr, :kj_burned, :duration_min,
                :start_time, :end_time, :raw_json)
    """, row)


def insert_cycle(conn: sqlite3.Connection, row: dict):
    conn.execute("""
        INSERT OR REPLACE INTO whoop_cycles
        (cycle_id, date, day_strain, avg_hr, max_hr, kj_burned, raw_json)
        VALUES (:cycle_id, :date, :day_strain, :avg_hr, :max_hr, :kj_burned, :raw_json)
    """, row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30, help="Days of history to generate")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Path to whoop.db")
    parser.add_argument("--reset", action="store_true",
                        help="Clear existing whoop_* rows before inserting")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    args = parser.parse_args()

    random.seed(args.seed)

    if not args.db.exists():
        print(f"ERROR: Database not found at {args.db}")
        print(f"Create it first with: sqlite3 {args.db} < schema.sql")
        sys.exit(1)

    conn = sqlite3.connect(args.db)

    if args.reset:
        print("Clearing existing rows...")
        conn.executescript("""
            DELETE FROM whoop_recovery;
            DELETE FROM whoop_sleep;
            DELETE FROM whoop_workouts;
            DELETE FROM whoop_cycles;
        """)

    today = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)

    n_recovery = 0
    n_sleep = 0
    n_workouts = 0
    n_cycles = 0

    for i, date in enumerate(daterange(today, args.days)):
        # Recovery
        rec = gen_recovery(date, i, args.days)
        insert_recovery(conn, rec)
        n_recovery += 1

        # Sleep
        slp = gen_sleep(date, i, args.days)
        insert_sleep(conn, slp)
        n_sleep += 1

        # Workouts
        workouts = gen_workouts(date, i, args.days)
        for w in workouts:
            insert_workout(conn, w)
            n_workouts += 1

        # Cycle
        cyc = gen_cycle(date, workouts)
        insert_cycle(conn, cyc)
        n_cycles += 1

    conn.commit()
    conn.close()

    print(f"\nGenerated {args.days} days of mock WHOOP data:")
    print(f"  Recovery records: {n_recovery}")
    print(f"  Sleep records:    {n_sleep}")
    print(f"  Workouts:         {n_workouts}")
    print(f"  Cycles:           {n_cycles}")
    print(f"\nDatabase: {args.db}")
    print("\nPatterns deliberately included for whoop-interpret to detect:")
    print("  - HRV downtrend in last 7 days")
    print("  - Elevated RHR in last 7 days")
    print("  - Sleep debt block in days 10-20")
    print("  - Workout-sleep correlation (late workouts -> poor sleep)")


if __name__ == "__main__":
    main()
