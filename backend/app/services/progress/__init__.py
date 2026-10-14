import uuid

from app.models.progress import ProgressEvent, ProgressEventCreate, UserProgressSummary
from app.services.progress.aggregator import build_user_progress_summary
from app.services.progress.store import insert_event, list_events_for_user
from app.services.progress.xp_rules import compute_xp
from app.services.question_service import get_question_by_id


async def record_progress_event(payload: ProgressEventCreate) -> ProgressEvent:
    subject = payload.subject
    topic = payload.topic
    difficulty: str | None = None

    if payload.question_id:
        question = await get_question_by_id(payload.question_id)
        if question is not None:
            dna = question.classification
            subject = dna.subject
            topic = dna.topic
            difficulty = dna.difficulty

    event = ProgressEvent(
        event_id=str(uuid.uuid4()),
        user_name=payload.user_name,
        activity_type=payload.activity_type,
        question_id=payload.question_id,
        is_correct=payload.is_correct,
        subject=subject,
        topic=topic,
        difficulty=difficulty,
        xp_earned=compute_xp(payload.activity_type, payload.is_correct),
    )
    await insert_event(event)
    return event


async def get_user_progress_summary(user_name: str) -> UserProgressSummary:
    events = await list_events_for_user(user_name)
    return build_user_progress_summary(user_name, events)


__all__ = ["record_progress_event", "get_user_progress_summary"]
