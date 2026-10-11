from app.models.analytics import ExamTrends, ImportantTopic, TopicFrequency

# Deterministic, documented weights -- sum to 1.0. Recurrence is
# weighted highest because "how often is this asked" is the strongest
# practical signal for exam prep; recency and coverage are weighted
# equally as secondary signals.
RECURRENCE_WEIGHT = 0.4
RECENCY_WEIGHT = 0.3
COVERAGE_WEIGHT = 0.3


def _recurrence_score(topic: TopicFrequency, max_count: int) -> float:
    """How often this topic is asked, relative to the most-asked topic."""
    if max_count <= 0:
        return 0.0
    return topic.total_count / max_count


def _recency_score(topic: TopicFrequency, min_year: int | None, max_year: int | None) -> float:
    """How recently this topic was last asked, relative to the corpus's
    observed year range. A topic with no identifiable year scores 0
    (recency cannot be assessed, so it is not rewarded)."""
    if topic.last_year is None or min_year is None or max_year is None:
        return 0.0
    if max_year == min_year:
        return 1.0
    return (topic.last_year - min_year) / (max_year - min_year)


def _coverage_score(topic: TopicFrequency, max_distinct_years: int) -> float:
    """How many distinct years this topic has appeared in, relative to
    the topic with the broadest year coverage."""
    if max_distinct_years <= 0:
        return 0.0
    return topic.distinct_years / max_distinct_years


def rank_important_topics(trends: ExamTrends, limit: int) -> list[ImportantTopic]:
    """Scores and ranks topics by importance = a weighted combination of
    recurrence, recency, and coverage, computed purely from the counts
    already present in `ExamTrends`. Deterministic, no LLM/embeddings.

    Topics with no `topic` classification are excluded -- there is
    nothing to rank them by.
    """
    candidates = [t for t in trends.by_topic if t.topic]
    if not candidates:
        return []

    max_count = max(t.total_count for t in candidates)
    max_distinct_years = max(t.distinct_years for t in candidates)

    scored: list[ImportantTopic] = []
    for topic in candidates:
        recurrence = _recurrence_score(topic, max_count)
        recency = _recency_score(topic, trends.min_year, trends.max_year)
        coverage = _coverage_score(topic, max_distinct_years)
        importance = (
            RECURRENCE_WEIGHT * recurrence + RECENCY_WEIGHT * recency + COVERAGE_WEIGHT * coverage
        )

        reason = (
            f"Asked {topic.total_count} time(s) across {topic.distinct_years} year(s)"
            + (f", most recently in {topic.last_year}" if topic.last_year else "")
            + f". Importance = {RECURRENCE_WEIGHT:.0%} recurrence ({recurrence:.2f}) + "
            f"{RECENCY_WEIGHT:.0%} recency ({recency:.2f}) + "
            f"{COVERAGE_WEIGHT:.0%} coverage ({coverage:.2f})."
        )

        scored.append(
            ImportantTopic(
                subject=topic.subject,
                topic=topic.topic,
                importance_score=round(importance, 3),
                recurrence_score=round(recurrence, 3),
                recency_score=round(recency, 3),
                coverage_score=round(coverage, 3),
                total_count=topic.total_count,
                distinct_years=topic.distinct_years,
                last_seen_year=topic.last_year,
                difficulty_distribution=topic.difficulty_distribution,
                reason=reason,
            )
        )

    scored.sort(key=lambda t: t.importance_score, reverse=True)
    return scored[:limit]
