from fastapi import APIRouter

from app.models.question import Question
from app.services.question_service import list_all_questions

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("", response_model=list[Question])
async def get_questions() -> list[Question]:
    return await list_all_questions()
