from typing import Any

from app.services.intelligence.material_embeddings import (
    ensure_material_embeddings_indexed,
    get_all_material_embeddings,
)
from app.services.intelligence.ollama_client import OllamaClient
from app.services.intelligence.similarity import cosine_similarity
from app.services.intelligence.tools.base import Tool
from app.services.intelligence.tools.text_utils import truncate_text
from app.services.material_service import get_chunk, get_material_by_id


async def _handler(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query", "")).strip()
    limit = int(args.get("limit") or 5)
    if not query:
        return {"error": "query is required", "results": []}

    client = OllamaClient()
    await ensure_material_embeddings_indexed(client)
    embeddings = await get_all_material_embeddings()
    if not embeddings:
        return {"results": [], "note": "No study materials are indexed yet."}

    [query_vector] = await client.embed([query])

    scored = sorted(
        (
            (cosine_similarity(query_vector, vector), chunk_id)
            for chunk_id, vector in embeddings.items()
        ),
        reverse=True,
    )

    results = []
    for score, chunk_id in scored[:limit]:
        material_id, _, page_str = chunk_id.partition(":")
        page = int(page_str)
        chunk = await get_chunk(material_id, page)
        if chunk is None:
            continue
        material = await get_material_by_id(material_id)
        results.append(
            {
                "material_id": material_id,
                "page": page,
                "similarity": round(score, 4),
                "text": truncate_text(chunk.text),
                "file": material.original_filename if material else None,
            }
        )

    return {"results": results}


material_search_tool = Tool(
    name="study_material_search",
    description=(
        "Semantically searches the student's uploaded study materials (textbooks, notes -- "
        "not exam papers) for content relevant to a topic, to ground an explanation. Use this "
        "when asked to explain or teach a concept."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The topic or concept to find material about."},
            "limit": {"type": "integer", "description": "Max number of results (default 5)."},
        },
        "required": ["query"],
    },
    handler=_handler,
)
