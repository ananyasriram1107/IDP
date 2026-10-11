from pydantic import BaseModel, Field


class DifficultyDistribution(BaseModel):
    easy: int = 0
    medium: int = 0
    hard: int = 0
    unclassified: int = 0


class YearCount(BaseModel):
    year: int
    count: int


class SubjectFrequency(BaseModel):
    subject: str
    total_count: int
    difficulty_distribution: DifficultyDistribution = Field(default_factory=DifficultyDistribution)


class ChapterFrequency(BaseModel):
    subject: str | None
    chapter: str
    total_count: int
    difficulty_distribution: DifficultyDistribution = Field(default_factory=DifficultyDistribution)


class TopicFrequency(BaseModel):
    subject: str | None
    topic: str
    total_count: int
    year_counts: list[YearCount] = Field(default_factory=list)
    first_year: int | None = None
    last_year: int | None = None
    distinct_years: int = 0
    difficulty_distribution: DifficultyDistribution = Field(default_factory=DifficultyDistribution)


class ExamTrends(BaseModel):
    total_questions: int
    questions_with_identified_year: int
    unclassified_questions: int
    min_year: int | None
    max_year: int | None
    by_year: list[YearCount]
    by_subject: list[SubjectFrequency]
    by_chapter: list[ChapterFrequency]
    by_topic: list[TopicFrequency]


class ImportantTopic(BaseModel):
    """A topic ranked by importance = a weighted combination of
    recurrence, recency, and coverage (see `scoring.py` for the exact
    formula). All scores are 0-1 normalized against the rest of the
    corpus; `reason` spells out the computation in plain language.
    """

    subject: str | None
    topic: str
    importance_score: float
    recurrence_score: float
    recency_score: float
    coverage_score: float
    total_count: int
    distinct_years: int
    last_seen_year: int | None
    difficulty_distribution: DifficultyDistribution
    reason: str
