from abc import ABC, abstractmethod

from app.models.classification import QuestionClassification


class QuestionClassifier(ABC):
    """Interface every classification backend must implement.

    The question-intelligence pipeline only ever depends on this
    interface, so adding a new backend (e.g. an Ollama/LLM classifier)
    never requires changing the database layer, the API, or callers.
    """

    @abstractmethod
    def classify(self, text: str) -> QuestionClassification:
        raise NotImplementedError
