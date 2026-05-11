from __future__ import annotations

import os
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient, ReturnDocument
from pymongo.database import Database


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DEFAULT_DATABASE_NAME = "woo_habits"


def mongo_uri() -> str:
    uri = os.getenv("MONGO_URI")
    if not uri:
        raise RuntimeError("MONGO_URI is not configured. Add it to woo_backend/.env.")
    return uri


def database_name() -> str:
    return os.getenv("MONGO_DB_NAME", DEFAULT_DATABASE_NAME)


@lru_cache(maxsize=1)
def client() -> MongoClient:
    return MongoClient(mongo_uri())


def db() -> Database:
    return client()[database_name()]


def init_db() -> None:
    database = db()
    database.habits.create_index([("id", ASCENDING)], unique=True)
    database.checkins.create_index(
        [("habit_id", ASCENDING), ("checkin_date", ASCENDING)], unique=True
    )
    database.checkins.create_index([("checkin_date", ASCENDING)])
    database.system_settings.create_index([("key", ASCENDING)], unique=True)
    database.outcome_rules.create_index([("id", ASCENDING)], unique=True)


def next_sequence(name: str) -> int:
    result = db().counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(result["value"])


def parse_iso_date(value: str | None) -> date:
    if not value:
        return date.today()
    return date.fromisoformat(value)


def streak_for_habit(habit_id: int, through_date: date | None = None) -> tuple[int, int, int]:
    rows = db().checkins.find(
        {"habit_id": habit_id},
        {"_id": 0, "checkin_date": 1, "completed": 1},
    ).sort("checkin_date", ASCENDING)
    completed_dates = {
        date.fromisoformat(row["checkin_date"])
        for row in rows
        if bool(row.get("completed"))
    }
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
