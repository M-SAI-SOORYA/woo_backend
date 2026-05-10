from __future__ import annotations

DEFAULT_XP_PER_LEVEL = 100

TITLE_LADDER = [
    (0, "Starter"),
    (5, "Consistent"),
    (10, "Focused"),
    (20, "Disciplined"),
    (30, "Relentless"),
    (40, "Elite"),
    (55, "Champion"),
    (70, "Master"),
    (85, "Legend"),
    (100, "Ascendant"),
]


def current_level(total_xp: int, xp_per_level: int = DEFAULT_XP_PER_LEVEL) -> int:
    required = max(xp_per_level, 1)
    return max(total_xp, 0) // required


def xp_progress(total_xp: int, xp_per_level: int = DEFAULT_XP_PER_LEVEL) -> dict[str, int]:
    safe_xp = max(total_xp, 0)
    required = max(xp_per_level, 1)
    return {
        "current": safe_xp % required,
        "required": required,
        "percent": int((safe_xp % required) / required * 100),
    }


def title_for_level(level: int) -> str:
    title = TITLE_LADDER[0][1]
    for required_level, candidate in TITLE_LADDER:
        if level >= required_level:
            title = candidate
    return title
