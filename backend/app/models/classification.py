from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DifficultyLevel(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuestionType(str, Enum):
    mcq = "mcq"
    numerical = "numerical"
    subjective = "subjective"
    true_false = "true_false"
    assertion_reason = "assertion_reason"
    match_the_following = "match_the_following"
    fill_in_the_blank = "fill_in_the_blank"
    other = "other"


class CognitiveLevel(str, Enum):
    remember = "remember"
    understand = "understand"
    apply = "apply"
    analyze = "analyze"
    evaluate = "evaluate"
    create = "create"


class ClassificationMethod(str, Enum):
    unclassified = "unclassified"
    rule_based = "rule_based"
    llm = "llm"


class QuestionClassification(BaseModel):
    """Question DNA: structured tags describing what a question is about.

    All fields are optional so a question can exist unclassified (the
    default) and be enriched later by any classifier backend without a
    schema migration.
    """

    model_config = ConfigDict(use_enum_values=True)

    subject: str | None = None
    chapter: str | None = None
    topic: str | None = None
    subtopics: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    difficulty: DifficultyLevel | None = None
    question_type: QuestionType | None = None
    cognitive_level: CognitiveLevel | None = None
    classified_by: ClassificationMethod = ClassificationMethod.unclassified
    confidence: float | None = None
