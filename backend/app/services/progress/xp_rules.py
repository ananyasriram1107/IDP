from app.models.progress import ActivityType

# Deterministic, documented XP table. Keyed by (activity_type, is_correct).
# A missing key (e.g. an ungraded activity) falls back to a flat 2 XP.
XP_RULES: dict[tuple[str, bool | None], int] = {
    ("practice", True): 10,
    ("practice", False): 3,
    ("quiz", True): 12,
    ("quiz", False): 4,
    ("flashcard", None): 2,
    ("teach_me", None): 5,
}

DEFAULT_XP = 2


def compute_xp(activity_type: ActivityType, is_correct: bool | None) -> int:
    return XP_RULES.get((activity_type, is_correct), DEFAULT_XP)
