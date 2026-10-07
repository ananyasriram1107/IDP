from app.core.config import settings
from app.services.classification.base import QuestionClassifier
from app.services.classification.llm_classifier import OllamaClassifier
from app.services.classification.rule_based import RuleBasedClassifier

_classifiers: dict[str, QuestionClassifier] = {}


def get_classifier(backend: str | None = None) -> QuestionClassifier:
    """Returns the active question classifier.

    `backend` defaults to `settings.classifier_backend`, so switching the
    whole pipeline over to an LLM-based classifier later is a config
    change, not a rewrite of the ingestion pipeline, database, or API.
    """
    backend = backend or settings.classifier_backend

    if backend not in _classifiers:
        if backend == "rule_based":
            _classifiers[backend] = RuleBasedClassifier()
        elif backend == "ollama":
            _classifiers[backend] = OllamaClassifier()
        else:
            raise ValueError(f"Unknown classifier backend: {backend}")

    return _classifiers[backend]
