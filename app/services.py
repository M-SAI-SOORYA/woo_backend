from __future__ import annotations

import random
from datetime import datetime

from pymongo import ASCENDING, DESCENDING, ReturnDocument

from .gamification import current_level, title_for_level, xp_progress
from .models import (
    CheckInRequest,
    HabitCreate,
    HabitUpdate,
    LegacyXpRequest,
    OutcomeRuleCreate,
    OutcomeRuleUpdate,
    RewardSystemSettings,
)
from .storage import db, next_sequence, parse_iso_date, streak_for_habit


def active_habit_xp_map() -> dict[int, int]:
    rows = db().habits.find({"active": True}, {"_id": 0, "id": 1, "xp": 1}).sort("id", ASCENDING)
    return {int(row["id"]): int(row["xp"]) for row in rows}


def active_level_requirement() -> int:
    pipeline = [
        {"$match": {"active": True}},
        {"$group": {"_id": None, "xp": {"$sum": "$xp"}}},
    ]
    row = next(db().habits.aggregate(pipeline), None)
    return max(int(row["xp"] if row else 0), 1)


def habit_today_state(habit_id: int):
    today = parse_iso_date(None).isoformat()
    row = db().checkins.find_one(
        {"habit_id": habit_id, "checkin_date": today},
        {"_id": 0, "completed": 1, "xp_delta": 1},
    )
    completed = bool(row["completed"]) if row else False
    return {
        "completed_today": completed,
        "locked_today": completed,
        "earned_today_xp": int(row["xp_delta"]) if row and completed else 0,
    }


def serialize_habit(row, xp_map=None):
    xp_map = xp_map if xp_map is not None else active_habit_xp_map()
    current_streak, best_streak, completions = streak_for_habit(int(row["id"]))
    today_state = habit_today_state(int(row["id"]))
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "category": row["category"],
        "stat": row["stat"],
        "xp": int(xp_map.get(int(row["id"]), row["xp"])),
        "penalty": int(row["penalty"]),
        "cadence": row["cadence"],
        "active": bool(row["active"]),
        "current_streak": current_streak,
        "best_streak": best_streak,
        "completions": completions,
        **today_state,
        "created_at": row["created_at"],
    }


def list_habits(include_inactive: bool = False):
    query = {} if include_inactive else {"active": True}
    xp_map = active_habit_xp_map()
    rows = db().habits.find(query).sort([("active", DESCENDING), ("id", ASCENDING)])
    return [serialize_habit(row, xp_map) for row in rows]


def create_habit(payload: HabitCreate):
    now = datetime.utcnow().isoformat()
    row = {
        "id": next_sequence("habits"),
        "name": payload.name,
        "category": payload.category,
        "stat": payload.stat,
        "xp": payload.xp,
        "penalty": payload.penalty,
        "cadence": payload.cadence.value,
        "active": True,
        "created_at": now,
    }
    db().habits.insert_one(row)
    return serialize_habit(row)


def update_habit(habit_id: int, payload: HabitUpdate):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return get_habit(habit_id)
    update_doc = {
        key: value.value if hasattr(value, "value") else value
        for key, value in updates.items()
    }
    row = db().habits.find_one_and_update(
        {"id": habit_id},
        {"$set": update_doc},
        return_document=ReturnDocument.AFTER,
    )
    return serialize_habit(row) if row else None


def delete_habit(habit_id: int) -> bool:
    result = db().habits.delete_one({"id": habit_id})
    if result.deleted_count:
        db().checkins.delete_many({"habit_id": habit_id})
    return result.deleted_count > 0


def get_habit(habit_id: int):
    row = db().habits.find_one({"id": habit_id})
    return serialize_habit(row) if row else None


def total_xp() -> int:
    row = next(db().checkins.aggregate([{"$group": {"_id": None, "xp": {"$sum": "$xp_delta"}}}]), None)
    return int(row["xp"] if row else 0)


def stat_totals():
    rows = db().habits.find({}, {"_id": 0, "id": 1, "stat": 1}).sort("id", ASCENDING)
    totals: dict[str, int] = {}
    for habit in rows:
        aggregate = next(
            db().checkins.aggregate(
                [
                    {"$match": {"habit_id": int(habit["id"])}},
                    {"$group": {"_id": None, "xp": {"$sum": "$xp_delta"}}},
                ]
            ),
            None,
        )
        totals[habit["stat"]] = totals.get(habit["stat"], 0) + int(aggregate["xp"] if aggregate else 0)
    return [{"stat": stat, "xp": xp} for stat, xp in totals.items()]


def serialize_outcome_rule(row):
    return {
        "id": int(row["id"]),
        "outcome_type": row["outcome_type"],
        "title": row["title"],
        "message": row["message"],
        "active": bool(row["active"]),
        "created_at": row["created_at"],
    }


def get_reward_system():
    settings = {
        row["key"]: int(row["value"])
        for row in db().system_settings.find({}, {"_id": 0, "key": 1, "value": 1})
    }
    rewards = [
        serialize_outcome_rule(row)
        for row in db().outcome_rules.find({"outcome_type": "reward"}).sort(
            [("active", DESCENDING), ("id", ASCENDING)]
        )
    ]
    penalties = [
        serialize_outcome_rule(row)
        for row in db().outcome_rules.find({"outcome_type": "penalty"}).sort(
            [("active", DESCENDING), ("id", ASCENDING)]
        )
    ]
    return {
        "settings": {
            "reward_level_interval": settings.get("reward_level_interval", 3),
            "penalty_failure_threshold": settings.get("penalty_failure_threshold", 1),
        },
        "rewards": rewards,
        "penalties": penalties,
    }


def update_reward_system_settings(payload: RewardSystemSettings):
    for key, value in payload.model_dump().items():
        db().system_settings.update_one(
            {"key": key},
            {"$set": {"key": key, "value": str(value)}},
            upsert=True,
        )
    return get_reward_system()


def create_outcome_rule(payload: OutcomeRuleCreate):
    row = {
        "id": next_sequence("outcome_rules"),
        "outcome_type": payload.outcome_type.value,
        "title": payload.title,
        "message": payload.message,
        "active": bool(payload.active),
        "created_at": datetime.utcnow().isoformat(),
    }
    db().outcome_rules.insert_one(row)
    return serialize_outcome_rule(row)


def update_outcome_rule(rule_id: int, payload: OutcomeRuleUpdate):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        row = db().outcome_rules.find_one({"id": rule_id})
        return serialize_outcome_rule(row) if row else None
    row = db().outcome_rules.find_one_and_update(
        {"id": rule_id},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    return serialize_outcome_rule(row) if row else None


def delete_outcome_rule(rule_id: int) -> bool:
    result = db().outcome_rules.delete_one({"id": rule_id})
    return result.deleted_count > 0


def choose_active_outcome(outcome_type: str):
    rows = list(
        db().outcome_rules.find(
            {"outcome_type": outcome_type, "active": True},
            {"_id": 0, "title": 1, "message": 1},
        ).sort("id", ASCENDING)
    )
    if not rows:
        return None
    row = random.choice(rows)
    return f"{row['title']}: {row['message']}"


def resolve_reward(previous_level: int, new_level: int):
    settings = get_reward_system()["settings"]
    interval = settings["reward_level_interval"]
    crossed_reward_level = new_level > previous_level and new_level % interval == 0
    return choose_active_outcome("reward") if crossed_reward_level else None


def resolve_penalty(failure_count: int):
    settings = get_reward_system()["settings"]
    threshold = settings["penalty_failure_threshold"]
    return choose_active_outcome("penalty") if failure_count >= threshold else None


def dashboard():
    habits = list_habits()
    total = total_xp()
    level_requirement = active_level_requirement()
    level = current_level(total, level_requirement)
    history = list_history(limit=7)
    return {
        "player": "Soorya Marri",
        "job": "Discipline RPG",
        "totalXp": total,
        "currentlevel": level,
        "title": title_for_level(level),
        "progress": xp_progress(total, level_requirement),
        "levelRequirement": level_requirement,
        "habits": habits,
        "stats": stat_totals(),
        "history": history,
        "today": today_status(),
        "rewardSystem": get_reward_system()["settings"],
    }


def today_status():
    today = parse_iso_date(None).isoformat()
    habits = list(db().habits.find({"active": True}, {"_id": 0, "id": 1}))
    habit_ids = [int(row["id"]) for row in habits]
    completed = db().checkins.count_documents(
        {"habit_id": {"$in": habit_ids}, "checkin_date": today, "completed": True}
    )
    total = len(habit_ids)
    return {
        "date": today,
        "completed": completed,
        "total": total,
        "percent": int((completed / total) * 100) if total else 0,
    }


def record_checkins(payload: CheckInRequest):
    checkin_date = parse_iso_date(payload.date)
    previous_total = total_xp()
    previous_level = current_level(previous_total, active_level_requirement())
    now = datetime.utcnow().isoformat()

    item_ids = [item.habit_id for item in payload.items]
    habits = {
        int(row["id"]): row
        for row in db().habits.find({"id": {"$in": item_ids}})
    } if item_ids else {}
    xp_map = active_habit_xp_map()
    applied_failures = 0

    for item in payload.items:
        habit = habits.get(item.habit_id)
        if not habit:
            continue
        existing = db().checkins.find_one(
            {"habit_id": item.habit_id, "checkin_date": checkin_date.isoformat()},
            {"_id": 0, "completed": 1, "xp_delta": 1},
        )
        if existing and existing["completed"] is True:
            continue
        xp_delta = xp_map.get(item.habit_id, 25) if item.completed else -int(habit["penalty"])
        if not item.completed:
            applied_failures += 1
        checkin_doc = {
            "habit_id": item.habit_id,
            "checkin_date": checkin_date.isoformat(),
            "completed": bool(item.completed),
            "xp_delta": xp_delta,
        }
        if existing:
            db().checkins.update_one(
                {"habit_id": item.habit_id, "checkin_date": checkin_date.isoformat()},
                {"$set": checkin_doc},
            )
        else:
            db().checkins.insert_one(
                {**checkin_doc, "id": next_sequence("checkins"), "created_at": now}
            )

    new_total = total_xp()
    new_level = current_level(new_total, active_level_requirement())
    return {
        "dashboard": dashboard(),
        "xpDelta": new_total - previous_total,
        "leveledUp": new_level > previous_level,
        "reward": resolve_reward(previous_level, new_level),
        "penalty": resolve_penalty(applied_failures),
    }


def list_history(limit: int | None = None):
    level_requirement = active_level_requirement()
    pipeline = [
        {
            "$group": {
                "_id": "$checkin_date",
                "totalXp": {"$sum": "$xp_delta"},
                "completed": {"$sum": {"$cond": ["$completed", 1, 0]}},
                "total": {"$sum": 1},
            }
        },
        {"$sort": {"_id": -1}},
    ]
    if limit:
        pipeline.append({"$limit": limit})
    rows = list(db().checkins.aggregate(pipeline))

    running = 0
    entries = []
    for row in reversed(rows):
        running += int(row["totalXp"])
        level = current_level(running, level_requirement)
        entries.append(
            {
                "_id": row["_id"],
                "dater": row["_id"],
                "date": row["_id"],
                "completed": int(row["completed"]),
                "total": int(row["total"]),
                "totalXp": int(row["totalXp"]),
                "currentlevel": level,
                "title": title_for_level(level),
                "rewards": "Earned on level milestones",
                "penalties": "Applied on missed habits",
            }
        )
    return list(reversed(entries))


def legacy_status():
    data = dashboard()
    stat_map = {item["stat"].lower(): item["xp"] for item in data["stats"]}
    return {
        "_id": "local-player",
        "gymXp": stat_map.get("strength", 0),
        "todoXp": stat_map.get("intelligence", 0),
        "dietXp": stat_map.get("vitality", 0),
        "socialXp": stat_map.get("charisma", 0),
        "dater": data["today"]["date"],
        "title": data["title"],
        "currentlevel": data["currentlevel"],
        "totalXp": data["totalXp"],
        "rewards": "No Rewards Right Now",
        "penalties": "No Penalties Till Now",
        "job": data["job"],
    }


def record_legacy_xp(payload: LegacyXpRequest):
    habits = list_habits()
    legacy_names = ["Workout", "Deep Work", "Clean Diet", "Social Confidence"]
    xp_values = [payload.gymXp, payload.todoXp, payload.dietXp, payload.socialXp]
    items = []
    for name, xp_value in zip(legacy_names, xp_values):
        habit = next((item for item in habits if item["name"] == name), None)
        if habit:
            items.append({"habit_id": habit["id"], "completed": xp_value > 0})
    return record_checkins(CheckInRequest(items=items))
