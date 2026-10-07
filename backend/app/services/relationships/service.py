from app.db.mongodb import get_database
from app.models.question import Question
from app.models.relationship import QuestionRelationship
from app.services.relationships.registry import get_relationship_detector

RELATIONSHIPS_COLLECTION = "question_relationships"
QUESTIONS_COLLECTION = "questions"


async def _load_all_questions() -> list[Question]:
    db = get_database()
    records = await db[QUESTIONS_COLLECTION].find().to_list(length=10000)
    return [
        Question(question_id=record["_id"], **{k: v for k, v in record.items() if k != "_id"})
        for record in records
    ]


async def _store_relationships(relationships: list[QuestionRelationship]) -> None:
    db = get_database()
    for relationship in relationships:
        await db[RELATIONSHIPS_COLLECTION].update_one(
            {"_id": relationship.relationship_id},
            {"$set": relationship.model_dump(exclude={"relationship_id"})},
            upsert=True,
        )


async def compute_and_store_relationships(new_questions: list[Question]) -> list[QuestionRelationship]:
    """Detects relationships between newly stored questions and the
    rest of the question corpus, and persists them.

    Pure text + Question DNA comparison, deterministic and offline --
    no embeddings or external calls, so this works without any
    RAG/vector infrastructure. Pairs are deduplicated and upserted by a
    stable id, so recomputation never grows the collection unbounded.
    """
    if not new_questions:
        return []

    detector = get_relationship_detector()
    all_questions = await _load_all_questions()

    seen_pairs: set[tuple[str, str]] = set()
    relationships: list[QuestionRelationship] = []

    for new_question in new_questions:
        for other in all_questions:
            if other.question_id == new_question.question_id:
                continue

            pair_key = tuple(sorted((new_question.question_id, other.question_id)))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            relationship = detector.detect_pair(new_question, other)
            if relationship:
                relationships.append(relationship)

    if relationships:
        await _store_relationships(relationships)

    return relationships


async def get_related_questions(question_id: str) -> list[dict]:
    db = get_database()
    cursor = db[RELATIONSHIPS_COLLECTION].find(
        {"$or": [{"source_id": question_id}, {"target_id": question_id}]}
    ).sort("confidence", -1)
    records = await cursor.to_list(length=200)

    results = []
    for record in records:
        other_id = (
            record["target_id"] if record["source_id"] == question_id else record["source_id"]
        )
        results.append(
            {
                "question_id": other_id,
                "type": record["type"],
                "confidence": record["confidence"],
                "reason": record["reason"],
            }
        )

    return results
