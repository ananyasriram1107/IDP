from collections import defaultdict

from app.models.progress import (
    ProgressEvent,
    RecentAttempt,
    SubjectAccuracy,
    TopicAccuracy,
    UserProgressSummary,
)

RECENT_ACTIVITY_LIMIT = 20

# A topic "checkpoint" unlocks once the student has attempted it enough
# times and is getting it right often enough. Deterministic, adjustable.
CHECKPOINT_MIN_ATTEMPTS = 3
CHECKPOINT_MIN_ACCURACY = 0.6


def _accuracy(correct: int, attempted: int) -> float:
    return round(correct / attempted, 4) if attempted else 0.0


def build_user_progress_summary(
    user_name: str, events: list[ProgressEvent], recent_limit: int = RECENT_ACTIVITY_LIMIT
) -> UserProgressSummary:
    """Pure, deterministic aggregation over a user's recorded activity --
    no DB access, directly unit-testable. Mirrors the grouping style of
    `analytics/aggregator.py`.
    """
    subject_attempted: dict[str, int] = defaultdict(int)
    subject_correct: dict[str, int] = defaultdict(int)
    topic_attempted: dict[tuple[str | None, str], int] = defaultdict(int)
    topic_correct: dict[tuple[str | None, str], int] = defaultdict(int)

    total_attempted = len(events)
    total_correct = sum(1 for e in events if e.is_correct)
    total_xp = sum(e.xp_earned for e in events)

    for event in events:
        if event.subject:
            subject_attempted[event.subject] += 1
            if event.is_correct:
                subject_correct[event.subject] += 1
        if event.topic:
            key = (event.subject, event.topic)
            topic_attempted[key] += 1
            if event.is_correct:
                topic_correct[key] += 1

    by_subject = [
        SubjectAccuracy(
            subject=subject, attempted=attempted, correct=subject_correct[subject],
            accuracy=_accuracy(subject_correct[subject], attempted),
        )
        for subject, attempted in sorted(
            subject_attempted.items(), key=lambda kv: kv[1], reverse=True
        )
    ]

    by_topic = []
    unlocked_checkpoints: list[str] = []
    for (subject, topic), attempted in sorted(
        topic_attempted.items(), key=lambda kv: kv[1], reverse=True
    ):
        correct = topic_correct[(subject, topic)]
        accuracy = _accuracy(correct, attempted)
        by_topic.append(
            TopicAccuracy(subject=subject, topic=topic, attempted=attempted, correct=correct, accuracy=accuracy)
        )
        if attempted >= CHECKPOINT_MIN_ATTEMPTS and accuracy >= CHECKPOINT_MIN_ACCURACY:
            unlocked_checkpoints.append(topic)

    # events are already newest-first from the store query
    recent_activity = [
        RecentAttempt(
            question_id=event.question_id,
            activity_type=event.activity_type,
            subject=event.subject,
            topic=event.topic,
            is_correct=event.is_correct,
            recorded_at=event.recorded_at,
        )
        for event in events[:recent_limit]
    ]

    return UserProgressSummary(
        user_name=user_name,
        total_attempted=total_attempted,
        total_correct=total_correct,
        accuracy=_accuracy(total_correct, total_attempted),
        total_xp=total_xp,
        unlocked_checkpoints=unlocked_checkpoints,
        by_subject=by_subject,
        by_topic=by_topic,
        recent_activity=recent_activity,
    )
