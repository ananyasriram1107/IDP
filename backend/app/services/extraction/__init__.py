from app.services.extraction.layout import extract_page_texts
from app.services.extraction.splitter import split_into_questions


def extract_questions_from_pdf(file_path: str) -> list[dict]:
    """Extracts questions from a PDF: layout-aware text extraction
    (handles genuine multi-column pages) followed by section-aware
    question splitting (handles numbering that restarts per section).

    Returns a list of dicts: {page, section, question_number, text}.
    """
    page_texts = extract_page_texts(file_path)
    return split_into_questions(page_texts)


__all__ = ["extract_questions_from_pdf"]
