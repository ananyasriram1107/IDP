import pytest

import app.services.intelligence.tools.dna_lookup as dna_lookup
import app.services.intelligence.tools.relationships_lookup as relationships_lookup
import app.services.intelligence.tools.semantic_search as semantic_search
import app.services.intelligence.tools.source_lookup as source_lookup
import app.services.intelligence.tools.trends_lookup as trends_lookup
from app.models.classification import QuestionClassification
from app.models.pdf import PDFDocument
from app.models.question import Question, QuestionSource
from app.services.intelligence.tools import get_tool_specs


def _question(question_id: str, text: str = "sample text", **classification_kwargs) -> Question:
    return Question(
        question_id=question_id,
        pdf_id="pdf-1",
        text=text,
        source=QuestionSource(file="2021_paper.pdf", page=1, question_number=1),
        classification=QuestionClassification(**classification_kwargs),
    )


def test_tool_registry_exposes_all_five_required_tools():
    specs = get_tool_specs()
    names = {spec["function"]["name"] for spec in specs}
    assert names == {
        "semantic_pyq_search",
        "question_dna_lookup",
        "question_relationships_lookup",
        "exam_trends_lookup",
        "question_source_lookup",
    }
    for spec in specs:
        assert spec["type"] == "function"
        assert "parameters" in spec["function"]


@pytest.mark.asyncio
async def test_dna_lookup_tool_by_question_id(monkeypatch):
    q = _question("q1", subject="Physics", topic="Mechanics")

    async def fake_get_question_by_id(question_id):
        assert question_id == "q1"
        return q

    monkeypatch.setattr(dna_lookup, "get_question_by_id", fake_get_question_by_id)

    result = await dna_lookup._handler({"question_id": "q1"})

    assert result["question_id"] == "q1"
    assert result["classification"]["subject"] == "Physics"


@pytest.mark.asyncio
async def test_dna_lookup_tool_missing_question_returns_error(monkeypatch):
    async def fake_get_question_by_id(question_id):
        return None

    monkeypatch.setattr(dna_lookup, "get_question_by_id", fake_get_question_by_id)

    result = await dna_lookup._handler({"question_id": "missing"})

    assert "error" in result


@pytest.mark.asyncio
async def test_dna_lookup_tool_filters_by_subject_and_topic(monkeypatch):
    questions = [
        _question("q1", subject="Physics", topic="Mechanics"),
        _question("q2", subject="Physics", topic="Thermodynamics"),
        _question("q3", subject="Chemistry", topic="Mechanics"),
    ]

    async def fake_list_all_questions():
        return questions

    monkeypatch.setattr(dna_lookup, "list_all_questions", fake_list_all_questions)

    result = await dna_lookup._handler({"subject": "Physics", "topic": "Mechanics"})

    assert result["total_matches"] == 1
    assert result["matches"][0]["question_id"] == "q1"


@pytest.mark.asyncio
async def test_relationships_lookup_tool_wraps_existing_service(monkeypatch):
    q = _question("q1", text="A block on a pulley...")

    async def fake_get_question_by_id(question_id):
        return q

    async def fake_get_related_questions(question_id):
        return [{"question_id": "q2", "type": "near_duplicate", "confidence": 0.9, "reason": "reworded"}]

    monkeypatch.setattr(relationships_lookup, "get_question_by_id", fake_get_question_by_id)
    monkeypatch.setattr(relationships_lookup, "get_related_questions", fake_get_related_questions)

    result = await relationships_lookup._handler({"question_id": "q1"})

    assert result["question_id"] == "q1"
    assert result["related"][0]["question_id"] == "q2"


@pytest.mark.asyncio
async def test_relationships_lookup_tool_requires_question_id():
    result = await relationships_lookup._handler({})
    assert "error" in result


@pytest.mark.asyncio
async def test_source_lookup_tool_wraps_pdf_and_question_services(monkeypatch):
    q = _question("q1", text="A block on a pulley...")
    pdf = PDFDocument(
        id="pdf-1",
        original_filename="2021_paper.pdf",
        stored_filename="pdf-1.pdf",
        size_bytes=100,
        page_count=10,
        question_count=5,
        status="processed",
        uploaded_at="2024-01-01T00:00:00Z",
    )

    async def fake_get_question_by_id(question_id):
        return q

    async def fake_get_pdf_by_id(pdf_id):
        assert pdf_id == "pdf-1"
        return pdf

    monkeypatch.setattr(source_lookup, "get_question_by_id", fake_get_question_by_id)
    monkeypatch.setattr(source_lookup, "get_pdf_by_id", fake_get_pdf_by_id)

    result = await source_lookup._handler({"question_id": "q1"})

    assert result["source"]["file"] == "2021_paper.pdf"
    assert result["pdf"]["original_filename"] == "2021_paper.pdf"


@pytest.mark.asyncio
async def test_trends_lookup_tool_default_mode(monkeypatch):
    class FakeTrends:
        def model_dump(self):
            return {"total_questions": 42}

    async def fake_compute_exam_trends():
        return FakeTrends()

    monkeypatch.setattr(trends_lookup, "compute_exam_trends", fake_compute_exam_trends)

    result = await trends_lookup._handler({})

    assert result["mode"] == "trends"
    assert result["trends"]["total_questions"] == 42


@pytest.mark.asyncio
async def test_trends_lookup_tool_important_topics_mode(monkeypatch):
    class FakeTopic:
        def model_dump(self):
            return {"topic": "Mechanics", "importance_score": 0.9}

    async def fake_compute_important_topics(limit):
        assert limit == 3
        return [FakeTopic()]

    monkeypatch.setattr(trends_lookup, "compute_important_topics", fake_compute_important_topics)

    result = await trends_lookup._handler({"mode": "important_topics", "limit": 3})

    assert result["mode"] == "important_topics"
    assert result["important_topics"][0]["topic"] == "Mechanics"


@pytest.mark.asyncio
async def test_semantic_search_tool_ranks_by_cosine_similarity(monkeypatch):
    q_match = _question("q_match", text="Pulley tension problem", subject="Physics", topic="Mechanics")
    q_other = _question("q_other", text="Organic chemistry reaction", subject="Chemistry", topic="Organic")

    async def fake_ensure_embeddings_indexed(client):
        return 0

    async def fake_get_all_embeddings():
        return {
            "q_match": [1.0, 0.0, 0.0],
            "q_other": [0.0, 1.0, 0.0],
        }

    async def fake_embed(self, texts, model=None):
        # The query embedding points the same direction as q_match's vector.
        return [[1.0, 0.0, 0.0]]

    async def fake_get_question_by_id(question_id):
        return {"q_match": q_match, "q_other": q_other}[question_id]

    monkeypatch.setattr(semantic_search, "ensure_embeddings_indexed", fake_ensure_embeddings_indexed)
    monkeypatch.setattr(semantic_search, "get_all_embeddings", fake_get_all_embeddings)
    monkeypatch.setattr(semantic_search.OllamaClient, "embed", fake_embed)
    monkeypatch.setattr(semantic_search, "get_question_by_id", fake_get_question_by_id)

    result = await semantic_search._handler({"query": "pulley", "limit": 2})

    assert result["results"][0]["question_id"] == "q_match"
    assert result["results"][0]["similarity"] == 1.0
    assert result["results"][1]["question_id"] == "q_other"
    assert result["results"][1]["similarity"] == 0.0


@pytest.mark.asyncio
async def test_semantic_search_tool_requires_query():
    result = await semantic_search._handler({"query": "  "})
    assert "error" in result
    assert result["results"] == []


@pytest.mark.asyncio
async def test_semantic_search_tool_truncates_oversized_question_text(monkeypatch):
    huge_text = "A" * 5000
    q = _question("q1", text=huge_text, subject="Physics", topic="Mechanics")

    async def fake_ensure_embeddings_indexed(client):
        return 0

    async def fake_get_all_embeddings():
        return {"q1": [1.0, 0.0]}

    async def fake_embed(self, texts, model=None):
        return [[1.0, 0.0]]

    async def fake_get_question_by_id(question_id):
        return q

    monkeypatch.setattr(semantic_search, "ensure_embeddings_indexed", fake_ensure_embeddings_indexed)
    monkeypatch.setattr(semantic_search, "get_all_embeddings", fake_get_all_embeddings)
    monkeypatch.setattr(semantic_search.OllamaClient, "embed", fake_embed)
    monkeypatch.setattr(semantic_search, "get_question_by_id", fake_get_question_by_id)

    result = await semantic_search._handler({"query": "anything"})

    returned_text = result["results"][0]["text"]
    assert len(returned_text) < len(huge_text)
    assert returned_text.endswith("...")


@pytest.mark.asyncio
async def test_source_lookup_tool_truncates_oversized_question_text(monkeypatch):
    huge_text = "B" * 5000
    q = _question("q1", text=huge_text)

    async def fake_get_question_by_id(question_id):
        return q

    async def fake_get_pdf_by_id(pdf_id):
        return None

    monkeypatch.setattr(source_lookup, "get_question_by_id", fake_get_question_by_id)
    monkeypatch.setattr(source_lookup, "get_pdf_by_id", fake_get_pdf_by_id)

    result = await source_lookup._handler({"question_id": "q1"})

    assert len(result["text"]) < len(huge_text)
    assert result["text"].endswith("...")
