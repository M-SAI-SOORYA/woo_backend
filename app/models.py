from enum import Enum
from pydantic import BaseModel, Field


class HabitCadence(str, Enum):
    daily = "daily"
    weekly = "weekly"


class HabitCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    category: str = Field(min_length=2, max_length=40)
    stat: str = Field(min_length=2, max_length=40)
    xp: int = Field(default=25, ge=1, le=100)
    penalty: int = Field(default=10, ge=0, le=100)
    cadence: HabitCadence = HabitCadence.daily


class HabitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    category: str | None = Field(default=None, min_length=2, max_length=40)
    stat: str | None = Field(default=None, min_length=2, max_length=40)
    xp: int | None = Field(default=None, ge=1, le=100)
    penalty: int | None = Field(default=None, ge=0, le=100)
    cadence: HabitCadence | None = None
    active: bool | None = None


class HabitOut(BaseModel):
    id: int
    name: str
    category: str
    stat: str
    xp: int
    penalty: int
    cadence: HabitCadence
    active: bool
    current_streak: int
    best_streak: int
    completions: int
    completed_today: bool
    locked_today: bool
    earned_today_xp: int
    created_at: str


class CheckInItem(BaseModel):
    habit_id: int
    completed: bool


class CheckInRequest(BaseModel):
    date: str | None = Field(default=None, description="ISO date, defaults to today")
    items: list[CheckInItem]


class LegacyXpRequest(BaseModel):
    gymXp: int = 0
    todoXp: int = 0
    dietXp: int = 0
    socialXp: int = 0


class OutcomeType(str, Enum):
    reward = "reward"
    penalty = "penalty"


class OutcomeRuleCreate(BaseModel):
    outcome_type: OutcomeType
    title: str = Field(min_length=2, max_length=80)
    message: str = Field(min_length=2, max_length=240)
    active: bool = True


class OutcomeRuleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=80)
    message: str | None = Field(default=None, min_length=2, max_length=240)
    active: bool | None = None


class RewardSystemSettings(BaseModel):
    reward_level_interval: int = Field(default=3, ge=1, le=50)
    penalty_failure_threshold: int = Field(default=1, ge=1, le=20)
