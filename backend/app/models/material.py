from datetime import datetime

from pydantic import BaseModel


class StudyMaterial(BaseModel):
    id: str
    original_filename: str
    stored_filename: str
    size_bytes: int
    page_count: int
    status: str
    uploaded_at: datetime


class MaterialChunk(BaseModel):
    material_id: str
    page: int
    text: str
