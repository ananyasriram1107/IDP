from typing import Any

from app.services.intelligence.tools.base import Tool
from app.services.question_service import get_question_by_id, list_all_questions


async def _handler(args: dict[str, Any]) -> dict[str, Any]:
    question_id = args.get("question_id")
    if question_id:
        question = await get_question_by_id(question_id)
        if question is None:
            return {"error": f"No question found with id {question_id}"}
        return {
            "question_id": question.question_id,
            "text": question.text,
            "classification": question.classification.model_dump(),
        }

    subject = args.get("subject")
    topic = args.get("topic")
    difficulty = args.get("difficulty")
    limit = int(args.get("limit") or 10)

    questions = await list_all_questions()
    matches = []
    for question in questions:
        dna = question.classification
        if subject and dna.subject != subject:
            continue
        if topic and dna.topic != topic:
            continue
        if difficulty and dna.difficulty != difficulty:
            continue
        matches.append(
            {
                "question_id": question.question_id,
                "text": question.text[:200],
                "classification": dna.model_dump(),
            }
        )

    return {"matches": matches[:limit], "total_matches": len(matches)}


dna_lookup_tool = Tool(
    name="question_dna_lookup",
    description=(
        "Looks up Question DNA (subject, chapter, topic, concepts, difficulty, question type, "
        "cognitive level) for one specific question by id, or lists questions matching given "
        "subject/topic/difficulty filters."
    ),
    parameters={
        "type": "object",
        "properties": {
            "question_id": {"type": "string", "description": "Specific question id to look up."},
            "subject": {"type": "string"},
            "topic": {"type": "string"},
            "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
            "limit": {"type": "integer", "description": "Max matches to return (default 10)."},
        },
        "required": [],
    },
    handler=_handler,
)
