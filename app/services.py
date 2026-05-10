from __future__ import annotations

import random
from datetime import datetime

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
from .storage import connect, parse_iso_date, streak_for_habit


def active_habit_xp_map(conn):
    rows = conn.execute(
        "SELECT id, xp FROM habits WHERE active = 1 ORDER BY id ASC"
    ).fetchall()
    return {row["id"]: row["xp"] for row in rows}


def active_level_requirement(conn) -> int:
    value = conn.execute(
        "SELECT COALESCE(SUM(xp), 0) FROM habits WHERE active = 1"
    ).fetchone()[0]
    return max(int(value or 0), 1)


def habit_today_state(conn, habit_id: int):
    today = parse_iso_date(None).isoformat()
    row = conn.execute(
        """
        SELECT completed, xp_delta
        FROM checkins
        WHERE habit_id = ? AND checkin_date = ?
        """,
        (habit_id, today),
    ).fetchone()
    completed = bool(row["completed"]) if row else False
    return {
        "completed_today": completed,
        "locked_today": completed,
        "earned_today_xp": int(row["xp_delta"]) if row and completed else 0,
    }


def serialize_habit(conn, row, xp_map=None):
    xp_map = xp_map if xp_map is not None else active_habit_xp_map(conn)
    current_streak, best_streak, completions = streak_for_habit(conn, row["id"])
    today_state = habit_today_state(conn, row["id"])
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "stat": row["stat"],
        "xp": xp_map.get(row["id"], row["xp"]),
        "penalty": row["penalty"],
        "cadence": row["cadence"],
        "active": bool(row["active"]),
        "current_streak": current_streak,
        "best_streak": best_streak,
        "completions": completions,
        **today_state,
        "created_at": row["created_at"],
    }


def list_habits(include_inactive: bool = False):
    with connect() as conn:
        query = "SELECT * FROM habits"
        if not include_inactive:
            query += " WHERE active = 1"
        query += " ORDER BY active DESC, id ASC"
        xp_map = active_habit_xp_map(conn)
        return [serialize_habit(conn, row, xp_map) for row in conn.execute(query).fetchall()]


def create_habit(payload: HabitCreate):
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO habits (name, category, stat, xp, penalty, cadence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                payload.category,
                payload.stat,
                payload.xp,
                payload.penalty,
                payload.cadence.value,
                datetime.utcnow().isoformat(),
            ),
        )
        row = conn.execute("SELECT * FROM habits WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return serialize_habit(conn, row)


def update_habit(habit_id: int, payload: HabitUpdate):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return get_habit(habit_id)
    columns = []
    values = []
    for key, value in updates.items():
        columns.append(f"{key} = ?")
        values.append(value.value if hasattr(value, "value") else int(value) if isinstance(value, bool) else value)
    values.append(habit_id)
    with connect() as conn:
        conn.execute(f"UPDATE habits SET {', '.join(columns)} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
        if row is None:
            return None
        return serialize_habit(conn, row)


def delete_habit(habit_id: int) -> bool:
    with connect() as conn:
        result = conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
        return result.rowcount > 0


def get_habit(habit_id: int):
    with connect() as conn:
        row = conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
        return serialize_habit(conn, row) if row else None


def total_xp() -> int:
    with connect() as conn:
        value = conn.execute("SELECT COALESCE(SUM(xp_delta), 0) FROM checkins").fetchone()[0]
        return int(value or 0)


def stat_totals():
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT h.stat, COALESCE(SUM(c.xp_delta), 0) as xp
            FROM habits h
            LEFT JOIN checkins c ON c.habit_id = h.id
            GROUP BY h.stat
            ORDER BY h.id ASC
            """
        ).fetchall()
        return [{"stat": row["stat"], "xp": row["xp"]} for row in rows]


def serialize_outcome_rule(row):
    return {
        "id": row["id"],
        "outcome_type": row["outcome_type"],
        "title": row["title"],
        "message": row["message"],
        "active": bool(row["active"]),
        "created_at": row["created_at"],
    }


def get_reward_system():
    with connect() as conn:
        settings = {
            row["key"]: int(row["value"])
            for row in conn.execute("SELECT key, value FROM system_settings").fetchall()
        }
        rewards = [
            serialize_outcome_rule(row)
            for row in conn.execute(
                "SELECT * FROM outcome_rules WHERE outcome_type = 'reward' ORDER BY active DESC, id ASC"
            ).fetchall()
        ]
        penalties = [
            serialize_outcome_rule(row)
            for row in conn.execute(
                "SELECT * FROM outcome_rules WHERE outcome_type = 'penalty' ORDER BY active DESC, id ASC"
            ).fetchall()
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
    with connect() as conn:
        for key, value in payload.model_dump().items():
            conn.execute(
                """
                INSERT INTO system_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, str(value)),
            )
    return get_reward_system()


def create_outcome_rule(payload: OutcomeRuleCreate):
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO outcome_rules (outcome_type, title, message, active, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload.outcome_type.value,
                payload.title,
                payload.message,
                int(payload.active),
                datetime.utcnow().isoformat(),
            ),
        )
        row = conn.execute("SELECT * FROM outcome_rules WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return serialize_outcome_rule(row)


def update_outcome_rule(rule_id: int, payload: OutcomeRuleUpdate):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        with connect() as conn:
            row = conn.execute("SELECT * FROM outcome_rules WHERE id = ?", (rule_id,)).fetchone()
            return serialize_outcome_rule(row) if row else None
    columns = []
    values = []
    for key, value in updates.items():
        columns.append(f"{key} = ?")
        values.append(int(value) if isinstance(value, bool) else value)
    values.append(rule_id)
    with connect() as conn:
        conn.execute(f"UPDATE outcome_rules SET {', '.join(columns)} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM outcome_rules WHERE id = ?", (rule_id,)).fetchone()
        return serialize_outcome_rule(row) if row else None


def delete_outcome_rule(rule_id: int) -> bool:
    with connect() as conn:
        result = conn.execute("DELETE FROM outcome_rules WHERE id = ?", (rule_id,))
        return result.rowcount > 0


def choose_active_outcome(outcome_type: str):
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT title, message
            FROM outcome_rules
            WHERE outcome_type = ? AND active = 1
            ORDER BY id ASC
            """,
            (outcome_type,),
        ).fetchall()
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
    with connect() as conn:
        level_requirement = active_level_requirement(conn)
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
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT h.id, c.completed
            FROM habits h
            LEFT JOIN checkins c ON c.habit_id = h.id AND c.checkin_date = ?
            WHERE h.active = 1
            """,
            (today,),
        ).fetchall()
        completed = sum(1 for row in rows if row["completed"] == 1)
        total = len(rows)
        return {"date": today, "completed": completed, "total": total, "percent": int((completed / total) * 100) if total else 0}


def record_checkins(payload: CheckInRequest):
    checkin_date = parse_iso_date(payload.date)
    previous_total = total_xp()
    with connect() as conn:
        level_requirement = active_level_requirement(conn)
    previous_level = current_level(previous_total, level_requirement)
    now = datetime.utcnow().isoformat()

    with connect() as conn:
        xp_map = active_habit_xp_map(conn)
        habits = {
            row["id"]: row
            for row in conn.execute(
                f"SELECT * FROM habits WHERE id IN ({','.join('?' for _ in payload.items)})",
                [item.habit_id for item in payload.items],
            ).fetchall()
        } if payload.items else {}
        applied_failures = 0
        for item in payload.items:
            habit = habits.get(item.habit_id)
            if not habit:
                continue
            existing = conn.execute(
                """
                SELECT completed, xp_delta
                FROM checkins
                WHERE habit_id = ? AND checkin_date = ?
                """,
                (item.habit_id, checkin_date.isoformat()),
            ).fetchone()
            if existing and existing["completed"] == 1:
                continue
            xp_delta = xp_map.get(item.habit_id, 25) if item.completed else -habit["penalty"]
            if not item.completed:
                applied_failures += 1
            conn.execute(
                """
                INSERT INTO checkins (habit_id, checkin_date, completed, xp_delta, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(habit_id, checkin_date) DO UPDATE SET
                    completed = excluded.completed,
                    xp_delta = excluded.xp_delta
                """,
                (item.habit_id, checkin_date.isoformat(), int(item.completed), xp_delta, now),
            )

    new_total = total_xp()
    with connect() as conn:
        new_level_requirement = active_level_requirement(conn)
    new_level = current_level(new_total, new_level_requirement)
    return {
        "dashboard": dashboard(),
        "xpDelta": new_total - previous_total,
        "leveledUp": new_level > previous_level,
        "reward": resolve_reward(previous_level, new_level),
        "penalty": resolve_penalty(applied_failures),
    }


def list_history(limit: int | None = None):
    with connect() as conn:
        level_requirement = active_level_requirement(conn)
        query = """
            SELECT
                c.checkin_date,
                SUM(c.xp_delta) as totalXp,
                SUM(CASE WHEN c.completed = 1 THEN 1 ELSE 0 END) as completed,
                COUNT(*) as total
            FROM checkins c
            GROUP BY c.checkin_date
            ORDER BY c.checkin_date DESC
        """
        if limit:
            query += " LIMIT ?"
            rows = conn.execute(query, (limit,)).fetchall()
        else:
            rows = conn.execute(query).fetchall()

    running = 0
    entries = []
    for row in reversed(rows):
        running += row["totalXp"]
        level = current_level(running, level_requirement)
        entries.append(
            {
                "_id": row["checkin_date"],
                "dater": row["checkin_date"],
                "date": row["checkin_date"],
                "completed": row["completed"],
                "total": row["total"],
                "totalXp": row["totalXp"],
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
