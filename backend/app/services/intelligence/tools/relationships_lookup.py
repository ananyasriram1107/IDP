from typing import Any

from app.services.intelligence.tools.base import Tool
from app.services.question_service import get_question_by_id
from app.services.relationships import get_related_questions


async def _handler(args: dict[str, Any]) -> dict[str, Any]:
    question_id = args.get("question_id")
    if not question_id:
        return {"error": "question_id is required"}

    question = await get_question_by_id(question_id)
    if question is None:
        return {"error": f"No question found with id {question_id}"}

    related = await get_related_questions(question_id)
    return {
        "question_id": question_id,
        "question_text": question.text,
        "related": related,
    }


relationships_lookup_tool = Tool(
    name="question_relationships_lookup",
    description=(
        "Finds relationships (exact_duplicate, near_duplicate, same_concept, variant, related) "
        "between a given question and other questions in the corpus -- i.e. its question family."
    ),
    parameters={
        "type": "object",
        "properties": {
            "question_id": {
                "type": "string",
                "description": "The question id to find relationships for.",
            },
        },
        "required": ["question_id"],
    },
    handler=_handler,
)
