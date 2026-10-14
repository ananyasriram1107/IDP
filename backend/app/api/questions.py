from fastapi import APIRouter, HTTPException

from app.models.question import Question
from app.models.relationship import RelatedQuestion
from app.services.question_service import get_question_by_id, list_all_questions
from app.services.relationships import get_related_questions

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("", response_model=list[Question])
async def get_questions(
    subject: str | None = None,
    topic: str | None = None,
    difficulty: str | None = None,
    year: int | None = None,
) -> list[Question]:
    return await list_all_questions(subject=subject, topic=topic, difficulty=difficulty, year=year)


@router.get("/{question_id}/related", response_model=list[RelatedQuestion])
async def get_question_related(question_id: str) -> list[RelatedQuestion]:
    question = await get_question_by_id(question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    related = await get_related_questions(question_id)
    return [RelatedQuestion(**r) for r in related]
