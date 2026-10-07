from fastapi import APIRouter, HTTPException, UploadFile

from app.models.pdf import PDFDocument
from app.models.question import Question
from app.services.pdf_service import get_pdf_by_id, list_pdfs, save_and_process_pdf
from app.services.question_service import get_questions_for_pdf

router = APIRouter(prefix="/pdf", tags=["pdf"])


@router.post("/upload", response_model=PDFDocument)
async def upload_pdf(file: UploadFile) -> PDFDocument:
    return await save_and_process_pdf(file)


@router.get("", response_model=list[PDFDocument])
async def get_pdfs() -> list[PDFDocument]:
    return await list_pdfs()


@router.get("/{doc_id}", response_model=PDFDocument)
async def get_pdf(doc_id: str) -> PDFDocument:
    document = await get_pdf_by_id(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="PDF not found")
    return document


@router.get("/{doc_id}/questions", response_model=list[Question])
async def get_pdf_questions(doc_id: str) -> list[Question]:
    document = await get_pdf_by_id(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="PDF not found")
    return await get_questions_for_pdf(doc_id)
