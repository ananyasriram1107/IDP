import os
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import settings
from app.db.mongodb import get_database
from app.models.material import MaterialChunk, StudyMaterial
from app.services.extraction.layout import extract_page_texts

MATERIALS_COLLECTION = "study_materials"
CHUNKS_COLLECTION = "material_chunks"


def _ensure_materials_dir() -> str:
    os.makedirs(settings.materials_dir, exist_ok=True)
    return settings.materials_dir


def build_chunks(material_id: str, page_texts: list[str]) -> list[MaterialChunk]:
    """Pure mapping from extracted per-page text to stored chunks --
    skips blank pages, 1-indexed to match how pages are referenced
    everywhere else in this codebase (QuestionSource.page etc).
    """
    return [
        MaterialChunk(material_id=material_id, page=page_number, text=text)
        for page_number, text in enumerate(page_texts, start=1)
        if text.strip()
    ]


async def save_and_process_material(file: UploadFile) -> StudyMaterial:
    """Uploads a study document (textbook/notes) and extracts its raw
    per-page text for later retrieval -- deliberately does NOT run
    question splitting, keeping this pipeline separate from PYQ
    extraction (`question_service.extract_and_store_questions`).
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    contents = await file.read()

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds the {settings.max_upload_size_mb}MB size limit",
        )

    material_id = str(uuid.uuid4())
    stored_filename = f"{material_id}.pdf"
    materials_dir = _ensure_materials_dir()
    file_path = os.path.join(materials_dir, stored_filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    try:
        reader = PdfReader(file_path)
        page_count = len(reader.pages)
    except PdfReadError:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF")

    original_filename = file.filename or stored_filename
    page_texts = extract_page_texts(file_path)

    db = get_database()
    chunks = build_chunks(material_id, page_texts)
    if chunks:
        await db[CHUNKS_COLLECTION].insert_many(
            [
                {
                    "_id": f"{chunk.material_id}:{chunk.page}",
                    **chunk.model_dump(),
                }
                for chunk in chunks
            ]
        )

    material = StudyMaterial(
        id=material_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        size_bytes=len(contents),
        page_count=page_count,
        status="processed",
        uploaded_at=datetime.now(timezone.utc),
    )

    await db[MATERIALS_COLLECTION].insert_one(
        {"_id": material.id, **material.model_dump(exclude={"id"})}
    )

    return material


async def get_material_by_id(material_id: str) -> StudyMaterial | None:
    db = get_database()
    record = await db[MATERIALS_COLLECTION].find_one({"_id": material_id})
    if record is None:
        return None
    return StudyMaterial(id=record["_id"], **{k: v for k, v in record.items() if k != "_id"})


async def list_materials() -> list[StudyMaterial]:
    db = get_database()
    cursor = db[MATERIALS_COLLECTION].find().sort("uploaded_at", -1)
    records = await cursor.to_list(length=100)
    return [
        StudyMaterial(id=record["_id"], **{k: v for k, v in record.items() if k != "_id"})
        for record in records
    ]


async def get_chunk(material_id: str, page: int) -> MaterialChunk | None:
    db = get_database()
    record = await db[CHUNKS_COLLECTION].find_one({"_id": f"{material_id}:{page}"})
    if record is None:
        return None
    return MaterialChunk(**{k: v for k, v in record.items() if k != "_id"})


async def get_material_chunks(material_id: str) -> list[MaterialChunk]:
    db = get_database()
    cursor = db[CHUNKS_COLLECTION].find({"material_id": material_id}).sort("page", 1)
    records = await cursor.to_list(length=5000)
    return [MaterialChunk(**{k: v for k, v in record.items() if k != "_id"}) for record in records]
