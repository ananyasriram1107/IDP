from fastapi import APIRouter, Query

from app.models.analytics import ExamTrends, ImportantTopic
from app.services.analytics import compute_exam_trends, compute_important_topics

router = APIRouter(prefix="/exam", tags=["exam"])


@router.get("/trends", response_model=ExamTrends)
async def get_exam_trends() -> ExamTrends:
    return await compute_exam_trends()


@router.get("/important-topics", response_model=list[ImportantTopic])
async def get_important_topics(limit: int = Query(10, ge=1, le=100)) -> list[ImportantTopic]:
    return await compute_important_topics(limit)
