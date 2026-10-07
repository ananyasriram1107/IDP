from abc import ABC, abstractmethod

from app.models.question import Question
from app.models.relationship import QuestionRelationship


class RelationshipDetector(ABC):
    """Interface every relationship-detection backend must implement.

    Mirrors `QuestionClassifier`: the rest of the pipeline only ever
    depends on this interface, so a future LLM-based detector can be
    swapped in via the registry without touching storage or the API.
    """

    @abstractmethod
    def detect_pair(self, a: Question, b: Question) -> QuestionRelationship | None:
        raise NotImplementedError
