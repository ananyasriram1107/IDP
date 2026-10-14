import hashlib

from app.db.mongodb import get_database
from app.services.intelligence.ollama_client import OllamaClient
from app.services.material_service import get_material_chunks, list_materials

MATERIAL_EMBEDDINGS_COLLECTION = "material_chunk_embeddings"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def ensure_material_embeddings_indexed(client: OllamaClient) -> int:
    """Embeds any study-material chunk that doesn't yet have a stored
    embedding, or whose text changed since it was last embedded.
    Incremental and idempotent, same pattern as
    `embeddings.ensure_embeddings_indexed` for questions.
    """
    materials = await list_materials()
    if not materials:
        return 0

    all_chunks = []
    for material in materials:
        all_chunks.extend(await get_material_chunks(material.id))
    if not all_chunks:
        return 0

    db = get_database()
    existing = await db[MATERIAL_EMBEDDINGS_COLLECTION].find(
        {}, {"_id": 1, "text_hash": 1}
    ).to_list(length=100000)
    existing_hashes = {doc["_id"]: doc.get("text_hash") for doc in existing}

    def chunk_id(chunk) -> str:
        return f"{chunk.material_id}:{chunk.page}"

    to_index = [c for c in all_chunks if existing_hashes.get(chunk_id(c)) != _hash_text(c.text)]
    if not to_index:
        return 0

    vectors = await client.embed([c.text for c in to_index])

    for chunk, vector in zip(to_index, vectors):
        await db[MATERIAL_EMBEDDINGS_COLLECTION].update_one(
            {"_id": chunk_id(chunk)},
            {
                "$set": {
                    "vector": vector,
                    "text_hash": _hash_text(chunk.text),
                    "material_id": chunk.material_id,
                    "page": chunk.page,
                }
            },
            upsert=True,
        )

    return len(to_index)


async def get_all_material_embeddings() -> dict[str, list[float]]:
    db = get_database()
    records = await db[MATERIAL_EMBEDDINGS_COLLECTION].find(
        {}, {"_id": 1, "vector": 1}
    ).to_list(length=100000)
    return {record["_id"]: record["vector"] for record in records}
