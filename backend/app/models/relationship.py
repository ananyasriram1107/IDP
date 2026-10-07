from enum import Enum

from pydantic import BaseModel, ConfigDict


class RelationshipType(str, Enum):
    exact_duplicate = "exact_duplicate"
    near_duplicate = "near_duplicate"
    same_concept = "same_concept"
    variant = "variant"
    related = "related"


class QuestionRelationship(BaseModel):
    """A detected relationship between two questions.

    `source_id`/`target_id` are a canonically ordered pair (sorted by
    question_id), not an origin/variant direction: detection is based on
    text + Question DNA similarity, which is symmetric, so there is no
    deterministic way to say which question came "first".
    """

    model_config = ConfigDict(use_enum_values=True)

    relationship_id: str
    source_id: str
    target_id: str
    type: RelationshipType
    confidence: float
    reason: str


class RelatedQuestion(BaseModel):
    """A relationship described from one question's point of view --
    `question_id` here is the *other* question in the pair."""

    question_id: str
    type: RelationshipType
    confidence: float
    reason: str
