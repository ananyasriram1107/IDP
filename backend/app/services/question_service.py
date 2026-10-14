import uuid

from app.db.mongodb import get_database
from app.models.question import Question, QuestionSource
from app.services.classification import get_classifier
from app.services.extraction import extract_questions_from_pdf

COLLECTION_NAME = "questions"


async def extract_and_store_questions(
    pdf_id: str, file_path: str, original_filename: str
) -> list[Question]:
    raw_questions = extract_questions_from_pdf(file_path)
    classifier = get_classifier()

    questions = [
        Question(
            question_id=str(uuid.uuid4()),
            pdf_id=pdf_id,
            text=raw["text"],
            source=QuestionSource(
                file=original_filename,
                page=raw["page"],
                question_number=raw["question_number"],
                section=raw["section"],
            ),
            classification=classifier.classify(raw["text"]),
        )
        for raw in raw_questions
    ]

    if questions:
        db = get_database()
        await db[COLLECTION_NAME].insert_many(
            [
                {"_id": q.question_id, **q.model_dump(exclude={"question_id"})}
                for q in questions
            ]
        )

    return questions


def build_question_filter_query(
    subject: str | None = None,
    topic: str | None = None,
    difficulty: str | None = None,
) -> dict:
    """Pure: builds the Mongo filter dict for the stored (non-derived)
    classification fields. `year` is handled separately in
    `filter_by_year` since it isn't a stored field."""
    query: dict = {}
    if subject:
        query["classification.subject"] = subject
    if topic:
        query["classification.topic"] = topic
    if difficulty:
        query["classification.difficulty"] = difficulty
    return query


def filter_by_year(questions: list[Question], year: int | None) -> list[Question]:
    """Pure: year isn't a stored field -- it's derived from the source
    filename, same as the analytics module does. No-op if year is None."""
    if year is None:
        return questions

    # Deferred import avoids a circular import (analytics imports this module).
    from app.services.analytics.year_extraction import extract_year

    return [q for q in questions if extract_year(q.source.file) == year]


async def list_all_questions(
    subject: str | None = None,
    topic: str | None = None,
    difficulty: str | None = None,
    year: int | None = None,
) -> list[Question]:
    db = get_database()

    query = build_question_filter_query(subject=subject, topic=topic, difficulty=difficulty)

    cursor = db[COLLECTION_NAME].find(query).sort(
        [("source.file", 1), ("source.page", 1), ("source.question_number", 1)]
    )
    records = await cursor.to_list(length=1000)
    questions = [
        Question(question_id=record["_id"], **{k: v for k, v in record.items() if k != "_id"})
        for record in records
    ]

    return filter_by_year(questions, year)


async def get_question_by_id(question_id: str) -> Question | None:
    db = get_database()
    record = await db[COLLECTION_NAME].find_one({"_id": question_id})
    if record is None:
        return None
    return Question(question_id=record["_id"], **{k: v for k, v in record.items() if k != "_id"})


async def get_questions_for_pdf(pdf_id: str) -> list[Question]:
    db = get_database()
    cursor = db[COLLECTION_NAME].find({"pdf_id": pdf_id}).sort(
        [("source.page", 1), ("source.question_number", 1)]
    )
    records = await cursor.to_list(length=1000)
    return [
        Question(question_id=record["_id"], **{k: v for k, v in record.items() if k != "_id"})
        for record in records
    ]
