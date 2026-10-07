from datetime import datetime

from pydantic import BaseModel


class PDFDocument(BaseModel):
    id: str
    original_filename: str
    stored_filename: str
    size_bytes: int
    page_count: int
    question_count: int
    status: str
    uploaded_at: datetime
