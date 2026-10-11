from typing import Any

from app.services.intelligence.embeddings import ensure_embeddings_indexed, get_all_embeddings
from app.services.intelligence.ollama_client import OllamaClient
from app.services.intelligence.similarity import cosine_similarity
from app.services.intelligence.tools.base import Tool
from app.services.intelligence.tools.text_utils import truncate_text
from app.services.question_service import get_question_by_id


async def _handler(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query", "")).strip()
    limit = int(args.get("limit") or 5)
    if not query:
        return {"error": "query is required", "results": []}

    client = OllamaClient()
    await ensure_embeddings_indexed(client)
    embeddings = await get_all_embeddings()
    if not embeddings:
        return {"results": [], "note": "No questions are indexed yet."}

    [query_vector] = await client.embed([query])

    scored = sorted(
        ((cosine_similarity(query_vector, vector), question_id) for question_id, vector in embeddings.items()),
        reverse=True,
    )

    results = []
    for score, question_id in scored[:limit]:
        question = await get_question_by_id(question_id)
        if question is None:
            continue
        results.append(
            {
                "question_id": question.question_id,
                "similarity": round(score, 4),
                "text": truncate_text(question.text),
                "subject": question.classification.subject,
                "topic": question.classification.topic,
                "source": question.source.model_dump(),
            }
        )

    return {"results": results}


semantic_search_tool = Tool(
    name="semantic_pyq_search",
    description=(
        "Semantically searches previously uploaded exam questions (PYQs) by meaning, not just "
        "keywords, using embedding similarity. Use this to find questions related to a topic "
        "or concept the user describes in natural language."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for, in natural language."},
            "limit": {"type": "integer", "description": "Max number of results (default 5)."},
        },
        "required": ["query"],
    },
    handler=_handler,
)
