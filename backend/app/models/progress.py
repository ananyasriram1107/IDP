from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

ActivityType = Literal["practice", "quiz", "flashcard", "teach_me"]


class ProgressEventCreate(BaseModel):
    """Request body for POST /progress/events. `user_name` is the
    localStorage display name used as a de-facto user id -- there is
    no real auth, so this is intentionally just a plain string key the
    client already has.
    """

    user_name: str
    activity_type: ActivityType = "practice"
    question_id: str | None = None
    is_correct: bool | None = None
    subject: str | None = None
    topic: str | None = None


class ProgressEvent(ProgressEventCreate):
    event_id: str
    difficulty: str | None = None
    xp_earned: int
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SubjectAccuracy(BaseModel):
    subject: str
    attempted: int
    correct: int
    accuracy: float


class TopicAccuracy(BaseModel):
    subject: str | None
    topic: str
    attempted: int
    correct: int
    accuracy: float


class RecentAttempt(BaseModel):
    question_id: str | None
    activity_type: str
    subject: str | None
    topic: str | None
    is_correct: bool | None
    recorded_at: datetime


class UserProgressSummary(BaseModel):
    user_name: str
    total_attempted: int
    total_correct: int
    accuracy: float
    total_xp: int
    unlocked_checkpoints: list[str]
    by_subject: list[SubjectAccuracy]
    by_topic: list[TopicAccuracy]
    recent_activity: list[RecentAttempt]
