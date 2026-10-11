from app.models.classification import QuestionClassification
from app.models.question import Question, QuestionSource
from app.services.analytics.aggregator import build_exam_trends
from app.services.analytics.scoring import rank_important_topics
from app.services.analytics.year_extraction import extract_year


def _question(
    question_id: str,
    file: str,
    subject: str | None = None,
    topic: str | None = None,
    difficulty: str | None = None,
) -> Question:
    return Question(
        question_id=question_id,
        pdf_id="pdf-1",
        text="placeholder text",
        source=QuestionSource(file=file, page=1, question_number=1),
        classification=QuestionClassification(subject=subject, topic=topic, difficulty=difficulty),
    )


def test_extract_year_finds_a_plausible_year_in_filename():
    assert extract_year("JEE_Main_2024_Shift_1.pdf") == 2024
    assert extract_year("2021_1_English.pdf") == 2021


def test_extract_year_returns_none_when_absent():
    assert extract_year("simple_questions.pdf") is None


def test_build_exam_trends_counts_by_year_subject_and_topic():
    questions = [
        _question("1", "2021_paper.pdf", subject="Physics", topic="Mechanics", difficulty="easy"),
        _question("2", "2021_paper.pdf", subject="Physics", topic="Mechanics", difficulty="medium"),
        _question("3", "2022_paper.pdf", subject="Physics", topic="Mechanics", difficulty="hard"),
        _question("4", "2022_paper.pdf", subject="Chemistry", topic="Organic Chemistry", difficulty="easy"),
        _question("5", "no_year_here.pdf", subject="Chemistry", topic="Organic Chemistry", difficulty="easy"),
    ]

    trends = build_exam_trends(questions)

    assert trends.total_questions == 5
    assert trends.questions_with_identified_year == 4
    assert trends.min_year == 2021
    assert trends.max_year == 2022

    year_map = {yc.year: yc.count for yc in trends.by_year}
    assert year_map == {2021: 2, 2022: 2}

    subject_map = {s.subject: s.total_count for s in trends.by_subject}
    assert subject_map == {"Physics": 3, "Chemistry": 2}

    mechanics = next(t for t in trends.by_topic if t.topic == "Mechanics")
    assert mechanics.total_count == 3
    assert mechanics.first_year == 2021
    assert mechanics.last_year == 2022
    assert mechanics.distinct_years == 2
    assert mechanics.difficulty_distribution.easy == 1
    assert mechanics.difficulty_distribution.medium == 1
    assert mechanics.difficulty_distribution.hard == 1

    organic = next(t for t in trends.by_topic if t.topic == "Organic Chemistry")
    # One occurrence has no identifiable year -- counted in total_count
    # but excluded from year-based fields.
    assert organic.total_count == 2
    assert organic.distinct_years == 1
    assert organic.last_year == 2022


def test_unclassified_questions_are_counted_but_not_grouped():
    questions = [
        _question("1", "2021_paper.pdf"),  # no subject/topic at all
        _question("2", "2021_paper.pdf", subject="Physics", topic="Mechanics"),
    ]

    trends = build_exam_trends(questions)

    assert trends.total_questions == 2
    assert trends.unclassified_questions == 1
    assert len(trends.by_topic) == 1


def test_important_topics_rewards_recurrence_recency_and_coverage():
    questions = [
        # "Mechanics": asked often, across many years, including the most recent one.
        _question("1", "2019_paper.pdf", subject="Physics", topic="Mechanics"),
        _question("2", "2021_paper.pdf", subject="Physics", topic="Mechanics"),
        _question("3", "2022_paper.pdf", subject="Physics", topic="Mechanics"),
        _question("4", "2023_paper.pdf", subject="Physics", topic="Mechanics"),
        # "Optics": asked once, long ago, never since.
        _question("5", "2019_paper.pdf", subject="Physics", topic="Optics"),
    ]

    trends = build_exam_trends(questions)
    ranked = rank_important_topics(trends, limit=10)

    assert [t.topic for t in ranked][0] == "Mechanics"
    mechanics = ranked[0]
    optics = next(t for t in ranked if t.topic == "Optics")

    assert mechanics.importance_score > optics.importance_score
    assert mechanics.recurrence_score == 1.0  # most-asked topic
    assert mechanics.recency_score == 1.0  # last asked in the most recent year
    assert optics.recency_score == 0.0  # last asked in the earliest year


def test_important_topics_excludes_unclassified_questions():
    questions = [
        _question("1", "2021_paper.pdf"),  # no topic
        _question("2", "2021_paper.pdf", subject="Physics", topic="Mechanics"),
    ]

    trends = build_exam_trends(questions)
    ranked = rank_important_topics(trends, limit=10)

    assert len(ranked) == 1
    assert ranked[0].topic == "Mechanics"


def test_rank_important_topics_respects_limit():
    questions = [
        _question(str(i), "2021_paper.pdf", subject="Physics", topic=f"Topic {i}")
        for i in range(5)
    ]

    trends = build_exam_trends(questions)
    ranked = rank_important_topics(trends, limit=2)

    assert len(ranked) == 2
