from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator

DEFAULT_HABITS = [
    ("Workout", "Body", "Strength", 25, 15, "daily"),
    ("Deep Work", "Mind", "Intelligence", 25, 10, "daily"),
    ("Clean Diet", "Health", "Vitality", 25, 10, "daily"),
    ("Social Confidence", "Presence", "Charisma", 25, 10, "daily"),
]

DEFAULT_SYSTEM_SETTINGS = {
    "reward_level_interval": "3",
    "penalty_failure_threshold": "1",
}

DEFAULT_REWARDS = [
    ("Recovery Break", "Take a guilt-free recovery break after earning this milestone."),
    ("Social Time", "Plan time with friends or family."),
    ("Useful Upgrade", "Buy one useful item that supports your routine."),
    ("Entertainment Pass", "Watch one episode or movie without multitasking."),
]

DEFAULT_PENALTIES = [
    ("Focus Reset", "No social media tomorrow."),
    ("Deep Work Block", "Complete one focused deep-work block."),
    ("Practice Set", "Solve 5 practice problems."),
    ("Environment Reset", "Clean your workspace before the next session."),
]


def database_path() -> Path:
    return Path(os.getenv("DATABASE_PATH", "woo_habits.db"))


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(database_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                stat TEXT NOT NULL,
                xp INTEGER NOT NULL DEFAULT 25,
                penalty INTEGER NOT NULL DEFAULT 10,
                cadence TEXT NOT NULL DEFAULT 'daily',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL,
                checkin_date TEXT NOT NULL,
                completed INTEGER NOT NULL,
                xp_delta INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(habit_id, checkin_date),
                FOREIGN KEY(habit_id) REFERENCES habits(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS outcome_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                outcome_type TEXT NOT NULL CHECK(outcome_type IN ('reward', 'penalty')),
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM habits").fetchone()[0]
        if count == 0:
            now = datetime.utcnow().isoformat()
            conn.executemany(
                """
                INSERT INTO habits (name, category, stat, xp, penalty, cadence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [(*habit, now) for habit in DEFAULT_HABITS],
            )

        settings_count = conn.execute("SELECT COUNT(*) FROM system_settings").fetchone()[0]
        if settings_count == 0:
            conn.executemany(
                "INSERT INTO system_settings (key, value) VALUES (?, ?)",
                DEFAULT_SYSTEM_SETTINGS.items(),
            )

        rules_count = conn.execute("SELECT COUNT(*) FROM outcome_rules").fetchone()[0]
        if rules_count == 0:
            now = datetime.utcnow().isoformat()
            conn.executemany(
                """
                INSERT INTO outcome_rules (outcome_type, title, message, created_at)
                VALUES ('reward', ?, ?, ?)
                """,
                [(*reward, now) for reward in DEFAULT_REWARDS],
            )
            conn.executemany(
                """
                INSERT INTO outcome_rules (outcome_type, title, message, created_at)
                VALUES ('penalty', ?, ?, ?)
                """,
                [(*penalty, now) for penalty in DEFAULT_PENALTIES],
            )


def parse_iso_date(value: str | None) -> date:
    if not value:
        return date.today()
    return date.fromisoformat(value)


def streak_for_habit(conn: sqlite3.Connection, habit_id: int, through_date: date | None = None) -> tuple[int, int, int]:
    rows = conn.execute(
        """
        SELECT checkin_date, completed
        FROM checkins
        WHERE habit_id = ?
        ORDER BY checkin_date ASC
        """,
        (habit_id,),
    ).fetchall()
    completed_dates = {date.fromisoformat(row["checkin_date"]) for row in rows if row["completed"]}
    completions = len(completed_dates)

    best = 0
    run = 0
    previous: date | None = None
    for completed_on in sorted(completed_dates):
        run = run + 1 if previous and completed_on == previous + timedelta(days=1) else 1
        best = max(best, run)
        previous = completed_on

    cursor = through_date or date.today()
    current = 0
    while cursor in completed_dates:
        current += 1
        cursor -= timedelta(days=1)

    return current, best, completions
