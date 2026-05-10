from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    CheckInRequest,
    HabitCreate,
    HabitOut,
    HabitUpdate,
    LegacyXpRequest,
    OutcomeRuleCreate,
    OutcomeRuleUpdate,
    RewardSystemSettings,
)
from .services import (
    create_outcome_rule,
    create_habit,
    dashboard,
    delete_outcome_rule,
    delete_habit,
    get_reward_system,
    legacy_status,
    list_habits,
    list_history,
    record_checkins,
    record_legacy_xp,
    update_outcome_rule,
    update_habit,
    update_reward_system_settings,
)
from .storage import init_db

app = FastAPI(title="Woo Habit Tracker API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/dashboard")
def get_dashboard():
    return dashboard()


@app.get("/api/habits", response_model=list[HabitOut])
def get_habits(include_inactive: bool = False):
    return list_habits(include_inactive=include_inactive)


@app.post("/api/habits", response_model=HabitOut, status_code=201)
def post_habit(payload: HabitCreate):
    return create_habit(payload)


@app.patch("/api/habits/{habit_id}", response_model=HabitOut)
def patch_habit(habit_id: int, payload: HabitUpdate):
    habit = update_habit(habit_id, payload)
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    return habit


@app.delete("/api/habits/{habit_id}", status_code=204)
def remove_habit(habit_id: int):
    if not delete_habit(habit_id):
        raise HTTPException(status_code=404, detail="Habit not found")


@app.post("/api/checkins")
def post_checkins(payload: CheckInRequest):
    return record_checkins(payload)


@app.get("/api/history")
def get_history():
    return list_history()


@app.get("/api/reward-system")
def read_reward_system():
    return get_reward_system()


@app.patch("/api/reward-system/settings")
def patch_reward_system_settings(payload: RewardSystemSettings):
    return update_reward_system_settings(payload)


@app.post("/api/reward-system/rules", status_code=201)
def post_outcome_rule(payload: OutcomeRuleCreate):
    return create_outcome_rule(payload)


@app.patch("/api/reward-system/rules/{rule_id}")
def patch_outcome_rule(rule_id: int, payload: OutcomeRuleUpdate):
    rule = update_outcome_rule(rule_id, payload)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@app.delete("/api/reward-system/rules/{rule_id}", status_code=204)
def remove_outcome_rule(rule_id: int):
    if not delete_outcome_rule(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")


@app.get("/get/item1")
def get_legacy_item():
    return legacy_status()


@app.get("/get/items")
def get_legacy_items():
    return list_history()


@app.post("/xp")
def post_legacy_xp(payload: LegacyXpRequest):
    return record_legacy_xp(payload)


@app.post("/datexp")
def post_legacy_datexp(payload: LegacyXpRequest):
    return record_legacy_xp(payload)
