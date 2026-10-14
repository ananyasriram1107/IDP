from datetime import datetime, timezone

from app.models.progress import ProgressEvent
from app.services.progress.aggregator import build_user_progress_summary
from app.services.progress.xp_rules import compute_xp


def _event(
    event_id: str,
    activity_type: str = "practice",
    is_correct: bool | None = None,
    subject: str | None = None,
    topic: str | None = None,
    xp_earned: int | None = None,
) -> ProgressEvent:
    return ProgressEvent(
        event_id=event_id,
        user_name="Aarav",
        activity_type=activity_type,
        question_id=f"q-{event_id}",
        is_correct=is_correct,
        subject=subject,
        topic=topic,
        xp_earned=xp_earned if xp_earned is not None else compute_xp(activity_type, is_correct),
        recorded_at=datetime.now(timezone.utc),
    )


def test_compute_xp_follows_the_documented_table():
    assert compute_xp("practice", True) == 10
    assert compute_xp("practice", False) == 3
    assert compute_xp("quiz", True) == 12
    assert compute_xp("quiz", False) == 4
    assert compute_xp("flashcard", None) == 2
    assert compute_xp("teach_me", None) == 5


def test_summary_is_empty_for_no_events():
    summary = build_user_progress_summary("Aarav", [])

    assert summary.total_attempted == 0
    assert summary.total_correct == 0
    assert summary.accuracy == 0.0
    assert summary.total_xp == 0
    assert summary.unlocked_checkpoints == []
    assert summary.by_subject == []
    assert summary.by_topic == []
    assert summary.recent_activity == []


def test_summary_computes_overall_accuracy_and_xp():
    events = [
        _event("1", is_correct=True),
        _event("2", is_correct=True),
        _event("3", is_correct=False),
    ]

    summary = build_user_progress_summary("Aarav", events)

    assert summary.total_attempted == 3
    assert summary.total_correct == 2
    assert summary.accuracy == round(2 / 3, 4)
    assert summary.total_xp == 10 + 10 + 3


def test_summary_groups_by_subject_and_topic():
    events = [
        _event("1", is_correct=True, subject="Physics", topic="Mechanics"),
        _event("2", is_correct=False, subject="Physics", topic="Mechanics"),
        _event("3", is_correct=True, subject="Chemistry", topic="Organic Chemistry"),
    ]

    summary = build_user_progress_summary("Aarav", events)

    physics = next(s for s in summary.by_subject if s.subject == "Physics")
    assert physics.attempted == 2
    assert physics.correct == 1
    assert physics.accuracy == 0.5

    mechanics = next(t for t in summary.by_topic if t.topic == "Mechanics")
    assert mechanics.attempted == 2
    assert mechanics.correct == 1


def test_events_without_subject_or_topic_count_in_totals_but_not_breakdowns():
    events = [_event("1", is_correct=True), _event("2", is_correct=True, subject="Physics", topic="Mechanics")]

    summary = build_user_progress_summary("Aarav", events)

    assert summary.total_attempted == 2
    assert len(summary.by_subject) == 1
    assert len(summary.by_topic) == 1


def test_checkpoint_unlocks_only_when_attempts_and_accuracy_both_cross_threshold():
    # Below the attempt threshold (2 < 3): not unlocked even with perfect accuracy.
    few_attempts = [_event(str(i), is_correct=True, subject="Physics", topic="Mechanics") for i in range(2)]
    summary = build_user_progress_summary("Aarav", few_attempts)
    assert "Mechanics" not in summary.unlocked_checkpoints

    # Enough attempts but low accuracy: not unlocked.
    low_accuracy = [
        _event("a", is_correct=True, subject="Physics", topic="Mechanics"),
        _event("b", is_correct=False, subject="Physics", topic="Mechanics"),
        _event("c", is_correct=False, subject="Physics", topic="Mechanics"),
    ]
    summary = build_user_progress_summary("Aarav", low_accuracy)
    assert "Mechanics" not in summary.unlocked_checkpoints

    # Enough attempts and sufficient accuracy: unlocked.
    enough = [
        _event("x", is_correct=True, subject="Physics", topic="Mechanics"),
        _event("y", is_correct=True, subject="Physics", topic="Mechanics"),
        _event("z", is_correct=False, subject="Physics", topic="Mechanics"),
    ]
    summary = build_user_progress_summary("Aarav", enough)
    assert "Mechanics" in summary.unlocked_checkpoints


def test_recent_activity_is_capped_and_preserves_store_order():
    # The store already returns newest-first; the aggregator should not reorder, only cap.
    events = [_event(str(i)) for i in range(5)]

    summary = build_user_progress_summary("Aarav", events, recent_limit=2)

    assert len(summary.recent_activity) == 2
    assert [a.question_id for a in summary.recent_activity] == ["q-0", "q-1"]
