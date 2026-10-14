from app.models.classification import QuestionClassification
from app.models.question import Question, QuestionSource
from app.services.question_service import build_question_filter_query, filter_by_year


def _question(question_id: str, file: str, **classification_kwargs) -> Question:
    return Question(
        question_id=question_id,
        pdf_id="pdf-1",
        text="sample",
        source=QuestionSource(file=file, page=1, question_number=1),
        classification=QuestionClassification(**classification_kwargs),
    )


def test_build_query_omits_unset_filters():
    assert build_question_filter_query() == {}


def test_build_query_includes_only_given_filters():
    query = build_question_filter_query(subject="Physics", difficulty="easy")

    assert query == {
        "classification.subject": "Physics",
        "classification.difficulty": "easy",
    }
    assert "classification.topic" not in query


def test_build_query_includes_all_three_when_given():
    query = build_question_filter_query(subject="Physics", topic="Mechanics", difficulty="hard")

    assert query == {
        "classification.subject": "Physics",
        "classification.topic": "Mechanics",
        "classification.difficulty": "hard",
    }


def test_filter_by_year_none_is_a_noop():
    questions = [_question("1", "2021_paper.pdf"), _question("2", "no_year.pdf")]

    assert filter_by_year(questions, None) == questions


def test_filter_by_year_keeps_only_matching_year():
    questions = [
        _question("1", "2021_paper.pdf"),
        _question("2", "2022_paper.pdf"),
        _question("3", "another_2021_set.pdf"),
    ]

    result = filter_by_year(questions, 2021)

    assert {q.question_id for q in result} == {"1", "3"}


def test_filter_by_year_excludes_questions_with_no_derivable_year():
    questions = [_question("1", "no_year_here.pdf")]

    assert filter_by_year(questions, 2021) == []
