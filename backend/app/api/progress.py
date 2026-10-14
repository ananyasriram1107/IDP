from fastapi import APIRouter

from app.models.progress import ProgressEvent, ProgressEventCreate, UserProgressSummary
from app.services.progress import get_user_progress_summary, record_progress_event

router = APIRouter(prefix="/progress", tags=["progress"])


@router.post("/events", response_model=ProgressEvent)
async def post_progress_event(payload: ProgressEventCreate) -> ProgressEvent:
    return await record_progress_event(payload)


@router.get("/{user_name}", response_model=UserProgressSummary)
async def get_progress(user_name: str) -> UserProgressSummary:
    return await get_user_progress_summary(user_name)
