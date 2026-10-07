from pydantic import BaseModel, Field

from app.models.classification import QuestionClassification


class QuestionSource(BaseModel):
    file: str
    page: int
    question_number: int
    section: str | None = None


class Question(BaseModel):
    question_id: str
    pdf_id: str
    text: str
    source: QuestionSource
    classification: QuestionClassification = Field(default_factory=QuestionClassification)
