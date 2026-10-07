import difflib
import re

from app.models.question import Question
from app.models.relationship import QuestionRelationship, RelationshipType
from app.services.relationships.base import RelationshipDetector

_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]")
_WHITESPACE_RE = re.compile(r"\s+")
_DIGIT_RE = re.compile(r"\d+")

NEAR_DUPLICATE_THRESHOLD = 0.85
VARIANT_NO_DIGIT_THRESHOLD = 0.90
VARIANT_MIN_IMPROVEMENT = 0.05
SAME_CONCEPT_MIN_SHARED = 2


def _normalize(text: str) -> str:
    lowered = text.lower()
    no_punctuation = _NON_ALNUM_RE.sub(" ", lowered)
    return _WHITESPACE_RE.sub(" ", no_punctuation).strip()


def _strip_digits(text: str) -> str:
    return _DIGIT_RE.sub("#", text)


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


class RuleBasedRelationshipDetector(RelationshipDetector):
    """Deterministic relationship detector using normalized-text
    similarity plus Question DNA (classification) overlap.

    No embeddings, vector search, or LLM calls -- same "offline,
    reproducible" philosophy as `RuleBasedClassifier`. Priority order
    when a pair matches more than one rule: exact_duplicate >
    near_duplicate > variant > same_concept > related.
    """

    def detect_pair(self, a: Question, b: Question) -> QuestionRelationship | None:
        first, second = sorted([a, b], key=lambda q: q.question_id)

        norm_a = _normalize(first.text)
        norm_b = _normalize(second.text)
        if not norm_a or not norm_b:
            return None

        if norm_a == norm_b:
            return self._build(
                first,
                second,
                RelationshipType.exact_duplicate,
                1.0,
                "Normalized question text is identical.",
            )

        ratio = _similarity(norm_a, norm_b)
        stripped_a, stripped_b = _strip_digits(norm_a), _strip_digits(norm_b)
        digits_differ = stripped_a != norm_a or stripped_b != norm_b
        ratio_no_digits = _similarity(stripped_a, stripped_b)

        # Numeric-substitution check runs before the near-duplicate check:
        # a question that is *only* different in its numbers is a more
        # specific, more useful signal ("variant") than the generic
        # "near duplicate" bucket, even when the raw ratio is already high.
        if (
            digits_differ
            and ratio_no_digits >= VARIANT_NO_DIGIT_THRESHOLD
            and (stripped_a == stripped_b or ratio_no_digits - ratio >= VARIANT_MIN_IMPROVEMENT)
        ):
            return self._build(
                first,
                second,
                RelationshipType.variant,
                round(ratio_no_digits, 2),
                f"Text matches ({ratio_no_digits:.2f}) once numeric values are ignored -- "
                "likely the same question with different numbers.",
            )

        if ratio >= NEAR_DUPLICATE_THRESHOLD:
            return self._build(
                first,
                second,
                RelationshipType.near_duplicate,
                round(ratio, 2),
                f"Normalized text similarity is {ratio:.2f}, indicating a reworded duplicate.",
            )

        return self._dna_relationship(first, second)

    def _dna_relationship(self, first: Question, second: Question) -> QuestionRelationship | None:
        dna_a = first.classification
        dna_b = second.classification

        concepts_a = {c.lower() for c in dna_a.concepts}
        concepts_b = {c.lower() for c in dna_b.concepts}
        shared_concepts = sorted(concepts_a & concepts_b)

        same_subject = bool(dna_a.subject) and dna_a.subject == dna_b.subject
        same_topic = bool(dna_a.topic) and dna_a.topic == dna_b.topic

        if same_topic and (len(shared_concepts) >= SAME_CONCEPT_MIN_SHARED or same_subject):
            confidence = min(0.9, 0.6 + 0.1 * len(shared_concepts))
            reason = f"Same topic ('{dna_a.topic}')"
            if shared_concepts:
                reason += f" and shared concept(s): {', '.join(shared_concepts)}."
            else:
                reason += "."
            return self._build(
                first, second, RelationshipType.same_concept, round(confidence, 2), reason
            )

        if same_subject or shared_concepts:
            confidence = min(0.6, 0.3 + 0.1 * len(shared_concepts))
            parts = []
            if same_subject:
                parts.append(f"subject '{dna_a.subject}'")
            if shared_concepts:
                parts.append(f"shared concept(s): {', '.join(shared_concepts)}")
            reason = "Share " + " and ".join(parts) + "."
            return self._build(
                first, second, RelationshipType.related, round(confidence, 2), reason
            )

        return None

    def _build(
        self,
        first: Question,
        second: Question,
        rel_type: RelationshipType,
        confidence: float,
        reason: str,
    ) -> QuestionRelationship:
        return QuestionRelationship(
            relationship_id=f"{first.question_id}::{second.question_id}",
            source_id=first.question_id,
            target_id=second.question_id,
            type=rel_type,
            confidence=confidence,
            reason=reason,
        )
