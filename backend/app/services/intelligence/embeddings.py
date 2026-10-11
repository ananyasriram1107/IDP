import hashlib

from app.db.mongodb import get_database
from app.services.intelligence.ollama_client import OllamaClient
from app.services.question_service import list_all_questions

EMBEDDINGS_COLLECTION = "question_embeddings"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def ensure_embeddings_indexed(client: OllamaClient) -> int:
    """Embeds any question that doesn't yet have a stored embedding, or
    whose text has changed since it was last embedded. Incremental and
    idempotent -- safe to call before every semantic search.

    Returns how many questions were (re)indexed.
    """
    questions = await list_all_questions()
    if not questions:
        return 0

    db = get_database()
    existing = await db[EMBEDDINGS_COLLECTION].find({}, {"_id": 1, "text_hash": 1}).to_list(
        length=100000
    )
    existing_hashes = {doc["_id"]: doc.get("text_hash") for doc in existing}

    to_index = [q for q in questions if existing_hashes.get(q.question_id) != _hash_text(q.text)]
    if not to_index:
        return 0

    vectors = await client.embed([q.text for q in to_index])

    for question, vector in zip(to_index, vectors):
        await db[EMBEDDINGS_COLLECTION].update_one(
            {"_id": question.question_id},
            {"$set": {"vector": vector, "text_hash": _hash_text(question.text)}},
            upsert=True,
        )

    return len(to_index)


async def get_all_embeddings() -> dict[str, list[float]]:
    db = get_database()
    records = await db[EMBEDDINGS_COLLECTION].find({}, {"_id": 1, "vector": 1}).to_list(
        length=100000
    )
    return {record["_id"]: record["vector"] for record in records}
