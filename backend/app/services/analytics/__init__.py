from app.models.analytics import ExamTrends, ImportantTopic
from app.services.analytics.aggregator import build_exam_trends
from app.services.analytics.scoring import rank_important_topics
from app.services.question_service import list_all_questions


async def compute_exam_trends() -> ExamTrends:
    questions = await list_all_questions()
    return build_exam_trends(questions)


async def compute_important_topics(limit: int = 10) -> list[ImportantTopic]:
    trends = await compute_exam_trends()
    return rank_important_topics(trends, limit)


__all__ = ["compute_exam_trends", "compute_important_topics"]
