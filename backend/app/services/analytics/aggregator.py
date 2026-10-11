from collections import defaultdict

from app.models.analytics import (
    ChapterFrequency,
    DifficultyDistribution,
    ExamTrends,
    SubjectFrequency,
    TopicFrequency,
    YearCount,
)
from app.models.question import Question
from app.services.analytics.year_extraction import extract_year


def _bump_difficulty(dist: DifficultyDistribution, difficulty: str | None) -> None:
    if difficulty == "easy":
        dist.easy += 1
    elif difficulty == "medium":
        dist.medium += 1
    elif difficulty == "hard":
        dist.hard += 1
    else:
        dist.unclassified += 1


def build_exam_trends(questions: list[Question]) -> ExamTrends:
    """Aggregates frequency, year coverage, and difficulty distribution
    from the existing Question DNA -- a pure, deterministic calculation
    over data already in MongoDB, no LLM involved.

    A question's exam year is derived from its source filename (e.g.
    "JEE_Main_2024_Shift_1.pdf" -> 2024); questions whose filename has
    no recognizable year are still counted everywhere else, just left
    out of year-based aggregates.
    """
    year_counts: dict[int, int] = defaultdict(int)

    subject_counts: dict[str, int] = defaultdict(int)
    subject_difficulty: dict[str, DifficultyDistribution] = defaultdict(DifficultyDistribution)

    chapter_counts: dict[tuple[str | None, str], int] = defaultdict(int)
    chapter_difficulty: dict[tuple[str | None, str], DifficultyDistribution] = defaultdict(
        DifficultyDistribution
    )

    topic_counts: dict[tuple[str | None, str], int] = defaultdict(int)
    topic_years: dict[tuple[str | None, str], dict[int, int]] = defaultdict(lambda: defaultdict(int))
    topic_difficulty: dict[tuple[str | None, str], DifficultyDistribution] = defaultdict(
        DifficultyDistribution
    )

    questions_with_year = 0
    unclassified = 0

    for question in questions:
        dna = question.classification
        year = extract_year(question.source.file)

        if year is not None:
            year_counts[year] += 1
            questions_with_year += 1

        if dna.subject:
            subject_counts[dna.subject] += 1
            _bump_difficulty(subject_difficulty[dna.subject], dna.difficulty)
        else:
            unclassified += 1

        if dna.chapter:
            chapter_key = (dna.subject, dna.chapter)
            chapter_counts[chapter_key] += 1
            _bump_difficulty(chapter_difficulty[chapter_key], dna.difficulty)

        if dna.topic:
            topic_key = (dna.subject, dna.topic)
            topic_counts[topic_key] += 1
            _bump_difficulty(topic_difficulty[topic_key], dna.difficulty)
            if year is not None:
                topic_years[topic_key][year] += 1

    all_years = sorted(year_counts)
    min_year = all_years[0] if all_years else None
    max_year = all_years[-1] if all_years else None

    by_topic = []
    for (subject, topic), count in topic_counts.items():
        years_for_topic = topic_years.get((subject, topic), {})
        sorted_years = sorted(years_for_topic)
        by_topic.append(
            TopicFrequency(
                subject=subject,
                topic=topic,
                total_count=count,
                year_counts=[
                    YearCount(year=y, count=years_for_topic[y]) for y in sorted_years
                ],
                first_year=sorted_years[0] if sorted_years else None,
                last_year=sorted_years[-1] if sorted_years else None,
                distinct_years=len(sorted_years),
                difficulty_distribution=topic_difficulty[(subject, topic)],
            )
        )
    by_topic.sort(key=lambda t: t.total_count, reverse=True)

    by_subject = [
        SubjectFrequency(
            subject=subject, total_count=count, difficulty_distribution=subject_difficulty[subject]
        )
        for subject, count in sorted(subject_counts.items(), key=lambda kv: kv[1], reverse=True)
    ]

    by_chapter = [
        ChapterFrequency(
            subject=subject,
            chapter=chapter,
            total_count=count,
            difficulty_distribution=chapter_difficulty[(subject, chapter)],
        )
        for (subject, chapter), count in sorted(
            chapter_counts.items(), key=lambda kv: kv[1], reverse=True
        )
    ]

    return ExamTrends(
        total_questions=len(questions),
        questions_with_identified_year=questions_with_year,
        unclassified_questions=unclassified,
        min_year=min_year,
        max_year=max_year,
        by_year=[YearCount(year=y, count=year_counts[y]) for y in all_years],
        by_subject=by_subject,
        by_chapter=by_chapter,
        by_topic=by_topic,
    )
