import re

from app.models.classification import (
    ClassificationMethod,
    CognitiveLevel,
    DifficultyLevel,
    QuestionClassification,
    QuestionType,
)
from app.services.classification.base import QuestionClassifier

# subject -> topic -> keywords that indicate that topic
SUBJECT_TOPIC_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "Physics": {
        "Mechanics": [
            "force",
            "velocity",
            "acceleration",
            "momentum",
            "friction",
            "pulley",
            "gravity",
            "newton's law",
            "tension",
            "projectile",
        ],
        "Electromagnetism": [
            "current",
            "voltage",
            "magnetic field",
            "electric field",
            "resistor",
            "capacitor",
            "circuit",
            "induction",
        ],
        "Thermodynamics": [
            "heat",
            "temperature",
            "entropy",
            "thermodynamics",
            "ideal gas",
            "specific heat",
        ],
        "Optics & Waves": [
            "lens",
            "mirror",
            "refraction",
            "reflection",
            "wavelength",
            "interference",
            "diffraction",
        ],
    },
    "Chemistry": {
        "Physical Chemistry": [
            "mole",
            "equilibrium",
            "oxidation",
            "reduction",
            "rate of reaction",
            "molarity",
            "ph of",
        ],
        "Organic Chemistry": [
            "organic",
            "alkane",
            "alkene",
            "alkyne",
            "functional group",
            "isomer",
            "hydrocarbon",
        ],
        "Inorganic Chemistry": [
            "periodic table",
            "ionic bond",
            "covalent bond",
            "coordination compound",
            "transition metal",
        ],
    },
    "Mathematics": {
        "Calculus": [
            "integral",
            "derivative",
            "differentiate",
            "integrate",
            "limit of",
            "rate of change",
        ],
        "Algebra": [
            "matrix",
            "polynomial",
            "quadratic equation",
            "determinant",
            "linear equation",
        ],
        "Trigonometry": [
            "sine",
            "cosine",
            "tangent",
            "trigonometric",
        ],
        "Probability & Statistics": [
            "probability",
            "variance",
            "standard deviation",
            "distribution",
            "mean of",
        ],
    },
    "Biology": {
        "Cell Biology": [
            "cell membrane",
            "organelle",
            "mitochondria",
            "nucleus",
            "cytoplasm",
        ],
        "Genetics": [
            "dna",
            "gene",
            "chromosome",
            "allele",
            "mutation",
        ],
        "Ecology": [
            "ecosystem",
            "population",
            "biodiversity",
            "food chain",
        ],
    },
}

QUESTION_TYPE_RULES: list[tuple[QuestionType, re.Pattern]] = [
    (QuestionType.assertion_reason, re.compile(r"\bassertion\b.{0,40}\breason\b", re.I)),
    (QuestionType.match_the_following, re.compile(r"match\s+the\s+following|match\s+column", re.I)),
    (QuestionType.true_false, re.compile(r"\btrue\s+or\s+false\b", re.I)),
    (QuestionType.fill_in_the_blank, re.compile(r"fill\s+in\s+the\s+blanks?|_{3,}", re.I)),
    (QuestionType.mcq, re.compile(r"(?:^|\s)\(?[a-d]\)\s", re.I)),
]

NUMERICAL_HINT_PATTERN = re.compile(
    r"\b(calculate|compute|find the value|determine|evaluate the)\b", re.I
)

COGNITIVE_LEVEL_RULES: list[tuple[CognitiveLevel, re.Pattern]] = [
    (CognitiveLevel.create, re.compile(r"\b(derive|design|formulate|propose|construct)\b", re.I)),
    (CognitiveLevel.evaluate, re.compile(r"\b(evaluate|justify|critique|assess)\b", re.I)),
    (CognitiveLevel.analyze, re.compile(r"\b(analyze|analyse|compare|differentiate|examine)\b", re.I)),
    (CognitiveLevel.apply, re.compile(r"\b(calculate|find|determine|solve|compute)\b", re.I)),
    (CognitiveLevel.understand, re.compile(r"\b(explain|describe|summarize|interpret|why does)\b", re.I)),
    (CognitiveLevel.remember, re.compile(r"\b(define|state|list|name|recall)\b", re.I)),
]

DIFFICULTY_BUMP_PATTERN = re.compile(r"\b(derive|prove|show that)\b", re.I)


class RuleBasedClassifier(QuestionClassifier):
    """Deterministic keyword/regex classifier.

    Acts as the default "Question DNA" backend: fast, offline, and
    reproducible. Intended to be swapped out for (or combined with) an
    LLM-based classifier later via the registry, without changing the
    `Question` model or any API contract.
    """

    def classify(self, text: str) -> QuestionClassification:
        lowered = text.lower()

        subject, topic, concepts = self._match_subject_topic(lowered)
        question_type = self._match_question_type(text)
        cognitive_level = self._match_cognitive_level(lowered)
        difficulty = self._estimate_difficulty(text, lowered)

        confidence = 0.6 if subject else 0.2

        return QuestionClassification(
            subject=subject,
            chapter=None,
            topic=topic,
            subtopics=[],
            concepts=concepts,
            difficulty=difficulty,
            question_type=question_type,
            cognitive_level=cognitive_level,
            classified_by=ClassificationMethod.rule_based,
            confidence=confidence,
        )

    def _match_subject_topic(
        self, lowered_text: str
    ) -> tuple[str | None, str | None, list[str]]:
        best_subject: str | None = None
        best_topic: str | None = None
        best_matches: list[str] = []

        for subject, topics in SUBJECT_TOPIC_KEYWORDS.items():
            for topic, keywords in topics.items():
                matches = [kw for kw in keywords if kw in lowered_text]
                if len(matches) > len(best_matches):
                    best_subject, best_topic, best_matches = subject, topic, matches

        concepts = [kw.title() for kw in best_matches[:5]]
        return best_subject, best_topic, concepts

    def _match_question_type(self, text: str) -> QuestionType | None:
        for question_type, pattern in QUESTION_TYPE_RULES:
            if pattern.search(text):
                return question_type

        if NUMERICAL_HINT_PATTERN.search(text) and re.search(r"\d", text):
            return QuestionType.numerical

        return QuestionType.subjective

    def _match_cognitive_level(self, lowered_text: str) -> CognitiveLevel | None:
        for level, pattern in COGNITIVE_LEVEL_RULES:
            if pattern.search(lowered_text):
                return level
        return None

    def _estimate_difficulty(self, text: str, lowered_text: str) -> DifficultyLevel:
        word_count = len(text.split())

        if word_count < 25:
            difficulty = DifficultyLevel.easy
        elif word_count <= 60:
            difficulty = DifficultyLevel.medium
        else:
            difficulty = DifficultyLevel.hard

        if DIFFICULTY_BUMP_PATTERN.search(lowered_text) and difficulty == DifficultyLevel.easy:
            difficulty = DifficultyLevel.medium
        elif DIFFICULTY_BUMP_PATTERN.search(lowered_text) and difficulty == DifficultyLevel.medium:
            difficulty = DifficultyLevel.hard

        return difficulty
