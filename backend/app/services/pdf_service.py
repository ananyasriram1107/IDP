import os
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import settings
from app.db.mongodb import get_database
from app.models.pdf import PDFDocument
from app.services.question_service import extract_and_store_questions
from app.services.relationships import compute_and_store_relationships

COLLECTION_NAME = "pdfs"


def _ensure_upload_dir() -> str:
    os.makedirs(settings.upload_dir, exist_ok=True)
    return settings.upload_dir


async def save_and_process_pdf(file: UploadFile) -> PDFDocument:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    contents = await file.read()

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds the {settings.max_upload_size_mb}MB size limit",
        )

    doc_id = str(uuid.uuid4())
    stored_filename = f"{doc_id}.pdf"
    upload_dir = _ensure_upload_dir()
    file_path = os.path.join(upload_dir, stored_filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    try:
        reader = PdfReader(file_path)
        page_count = len(reader.pages)
    except PdfReadError:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF")

    original_filename = file.filename or stored_filename
    questions = await extract_and_store_questions(doc_id, file_path, original_filename)
    await compute_and_store_relationships(questions)

    document = PDFDocument(
        id=doc_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        size_bytes=len(contents),
        page_count=page_count,
        question_count=len(questions),
        status="processed",
        uploaded_at=datetime.now(timezone.utc),
    )

    db = get_database()
    await db[COLLECTION_NAME].insert_one(
        {"_id": document.id, **document.model_dump(exclude={"id"})}
    )

    return document


async def get_pdf_by_id(doc_id: str) -> PDFDocument | None:
    db = get_database()
    record = await db[COLLECTION_NAME].find_one({"_id": doc_id})
    if record is None:
        return None
    return PDFDocument(id=record["_id"], **{k: v for k, v in record.items() if k != "_id"})


async def list_pdfs() -> list[PDFDocument]:
    db = get_database()
    cursor = db[COLLECTION_NAME].find().sort("uploaded_at", -1)
    records = await cursor.to_list(length=100)
    return [
        PDFDocument(id=record["_id"], **{k: v for k, v in record.items() if k != "_id"})
        for record in records
    ]
