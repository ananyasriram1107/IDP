from typing import Any

from app.services.intelligence.tools.base import Tool
from app.services.intelligence.tools.text_utils import truncate_text
from app.services.pdf_service import get_pdf_by_id
from app.services.question_service import get_question_by_id


async def _handler(args: dict[str, Any]) -> dict[str, Any]:
    question_id = args.get("question_id")
    if not question_id:
        return {"error": "question_id is required"}

    question = await get_question_by_id(question_id)
    if question is None:
        return {"error": f"No question found with id {question_id}"}

    pdf = await get_pdf_by_id(question.pdf_id)

    return {
        "question_id": question.question_id,
        "text": truncate_text(question.text),
        "source": question.source.model_dump(),
        "pdf": pdf.model_dump() if pdf else None,
    }


source_lookup_tool = Tool(
    name="question_source_lookup",
    description=(
        "Looks up the exact source/provenance of a question: originating PDF file, page, "
        "section, question number, and upload metadata."
    ),
    parameters={
        "type": "object",
        "properties": {
            "question_id": {"type": "string", "description": "The question id to look up."},
        },
        "required": ["question_id"],
    },
    handler=_handler,
)
