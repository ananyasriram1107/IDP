from fastapi import APIRouter

from app.models.intelligence import IntelligenceQueryRequest, IntelligenceQueryResponse
from app.services.intelligence import run_agent

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.post("/query", response_model=IntelligenceQueryResponse)
async def post_intelligence_query(request: IntelligenceQueryRequest) -> IntelligenceQueryResponse:
    return await run_agent(request.query)
