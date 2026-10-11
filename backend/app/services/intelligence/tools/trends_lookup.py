from typing import Any

from app.services.analytics import compute_exam_trends, compute_important_topics
from app.services.intelligence.tools.base import Tool


async def _handler(args: dict[str, Any]) -> dict[str, Any]:
    mode = args.get("mode", "trends")

    if mode == "important_topics":
        limit = int(args.get("limit") or 10)
        topics = await compute_important_topics(limit)
        return {"mode": mode, "important_topics": [t.model_dump() for t in topics]}

    trends = await compute_exam_trends()
    return {"mode": "trends", "trends": trends.model_dump()}


trends_lookup_tool = Tool(
    name="exam_trends_lookup",
    description=(
        "Retrieves exam-wide statistics: question frequency by year/subject/chapter/topic and "
        "difficulty distribution (mode='trends', the default), or the topics ranked by "
        "importance -- recurrence + recency + coverage (mode='important_topics')."
    ),
    parameters={
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["trends", "important_topics"],
                "description": "Which report to retrieve.",
            },
            "limit": {
                "type": "integer",
                "description": "For mode='important_topics', how many topics to return.",
            },
        },
        "required": [],
    },
    handler=_handler,
)
