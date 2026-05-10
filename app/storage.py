from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Iterator


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
