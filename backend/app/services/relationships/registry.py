from app.core.config import settings
from app.services.relationships.base import RelationshipDetector
from app.services.relationships.rule_based import RuleBasedRelationshipDetector

_detectors: dict[str, RelationshipDetector] = {}


def get_relationship_detector(backend: str | None = None) -> RelationshipDetector:
    """Returns the active relationship detector.

    `backend` defaults to `settings.relationship_detector_backend`, so
    adding an LLM-based detector later is a config change (plus a new
    `RelationshipDetector` implementation), not a rewrite of the
    computation pipeline, storage, or API.
    """
    backend = backend or settings.relationship_detector_backend

    if backend not in _detectors:
        if backend == "rule_based":
            _detectors[backend] = RuleBasedRelationshipDetector()
        else:
            raise ValueError(f"Unknown relationship detector backend: {backend}")

    return _detectors[backend]
