from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """A piece of retrieved, tool-sourced fact.

    Never written by the LLM -- populated directly from tool results,
    so retrieved PYQ facts and the LLM's generated explanation
    (`IntelligenceQueryResponse.answer`) are always structurally
    separate, never conflated.
    """

    type: str
    question_id: str | None = None
    summary: str
    data: dict = Field(default_factory=dict)


class SourceReference(BaseModel):
    """A question/source citation, derived deterministically from tool
    results (not from the LLM's text)."""

    question_id: str
    file: str
    page: int
    question_number: int
    section: str | None = None


class AgentStep(BaseModel):
    step: int
    type: str  # "tool_call" | "final_answer" | "error"
    tool: str | None = None
    arguments: dict | None = None
    result_summary: str | None = None


class IntelligenceQueryRequest(BaseModel):
    query: str


class IntelligenceQueryResponse(BaseModel):
    answer: str
    evidence: list[EvidenceItem]
    sources: list[SourceReference]
    steps: list[AgentStep]
    tool_calls_made: int
    grounded: bool
    error: str | None = None
