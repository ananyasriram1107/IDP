from app.models.classification import QuestionClassification
from app.services.classification.base import QuestionClassifier


class OllamaClassifier(QuestionClassifier):
    """Placeholder for a future local-LLM (Ollama) classifier backend.

    Not implemented yet. Once a model/prompt is chosen, implement
    `classify` to call Ollama and map its output onto
    `QuestionClassification` (set `classified_by=ClassificationMethod.llm`).
    Switching the active backend to this class is a one-line change in
    `app/services/classification/registry.py` (or `settings.classifier_backend`)
    — no changes to the database schema or API are needed.
    """

    def __init__(self, model: str = "llama3"):
        self.model = model

    def classify(self, text: str) -> QuestionClassification:
        raise NotImplementedError("Ollama-based classification is not implemented yet")
