from pathlib import Path

from app.services.extraction import extract_questions_from_pdf

FIXTURES = Path(__file__).parent / "fixtures"


def test_simple_single_column_pdf_extracts_each_question():
    """Baseline case that already worked before this fix: a clean,
    single-column PDF with plainly numbered questions ("17.", "18.", ...).
    """
    questions = extract_questions_from_pdf(str(FIXTURES / "simple_questions.pdf"))

    assert len(questions) == 4
    numbers = [q["question_number"] for q in questions]
    assert numbers == [17, 18, 19, 20]

    assert questions[0]["page"] == 1
    assert "acceleration" in questions[0]["text"]

    # Last question is on the second page and was not corrupted by a
    # false-positive column split on a sparse/single-line page.
    assert questions[3]["page"] == 2
    assert questions[3]["text"] == "State and explain Newton's second law of motion with an example."


def test_question_spanning_a_page_break_is_captured_in_full():
    """A question whose text continues onto the next page must be
    captured as one complete question, not cut off at the page boundary.
    """
    questions = extract_questions_from_pdf(str(FIXTURES / "page_spanning_question.pdf"))

    assert len(questions) == 3

    spanning = next(q for q in questions if q["question_number"] == 18)
    assert spanning["page"] == 1  # starting page
    assert "tension in the string" in spanning["text"]
    assert "linear acceleration of the system" in spanning["text"]

    last = next(q for q in questions if q["question_number"] == 19)
    assert last["page"] == 2


def test_genuine_two_column_page_is_read_left_then_right():
    """A real two-column layout must be detected and read column by
    column (not interleaved line-by-line), and repeated question
    numbers across sections must stay distinguishable via `section`.
    """
    questions = extract_questions_from_pdf(str(FIXTURES / "two_column_sections.pdf"))

    assert len(questions) == 6

    sections = [q["section"] for q in questions]
    numbers = [q["question_number"] for q in questions]

    # Left column (Section 1, Q1-3) must be read in full before the
    # right column (Section 2, Q1-3) -- not interleaved line by line.
    assert sections == ["Section 1"] * 3 + ["Section 2"] * 3
    assert numbers == [1, 2, 3, 1, 2, 3]

    assert "frictionless pulley" in questions[1]["text"]
    assert "simple pendulum" in questions[5]["text"]


def test_single_line_page_does_not_falsely_trigger_a_column_split():
    """Regression guard: a page with very little text must not be
    mistaken for two columns just because of ordinary word spacing.
    """
    questions = extract_questions_from_pdf(str(FIXTURES / "simple_questions.pdf"))
    last = questions[-1]

    assert "\n" not in last["text"]
    assert last["text"].count("Newton's") == 1


def test_real_multi_subject_exam_pdf_extracts_all_questions():
    """Regression test for the reported bug: a real, multi-subject JEE
    Advanced paper (29 pages, three subjects of ~19 questions each,
    numbering restarting per section/subject) used to produce only 2
    giant pseudo-questions. It must now yield each individual question.
    """
    questions = extract_questions_from_pdf(str(FIXTURES / "jee_advanced_2021_paper1.pdf"))

    assert len(questions) == 57
    assert all(q["text"] for q in questions)

    first = questions[0]
    assert first["page"] == 1
    assert first["section"] == "Section 1"
    assert first["question_number"] == 1
    assert "Vernier calipers" in first["text"]

    last = questions[-1]
    assert last["page"] == 29
    assert last["section"] == "Section 4"
    assert last["question_number"] == 19

    # Question numbering must be allowed to restart per section/subject
    # rather than being treated as one global monotonic sequence.
    ones = [q for q in questions if q["question_number"] == 1]
    assert len(ones) == 3
    assert {q["page"] for q in ones} == {1, 12, 22}

    # Page and section metadata must be preserved for every question.
    assert all(q["page"] is not None for q in questions)
    assert all(q["section"] is not None for q in questions)
