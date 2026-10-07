from app.models.classification import QuestionClassification
from app.models.question import Question, QuestionSource
from app.models.relationship import RelationshipType
from app.services.relationships.rule_based import RuleBasedRelationshipDetector


def _question(question_id: str, text: str, **classification_kwargs) -> Question:
    return Question(
        question_id=question_id,
        pdf_id="pdf-1",
        text=text,
        source=QuestionSource(file="f.pdf", page=1, question_number=1),
        classification=QuestionClassification(**classification_kwargs),
    )


def test_identical_text_is_exact_duplicate():
    detector = RuleBasedRelationshipDetector()
    a = _question("a", "A particle of mass 2 kg moves under a force F = 3x N.")
    b = _question("b", "a particle of mass 2 kg moves under a force f = 3x n.")

    relationship = detector.detect_pair(a, b)

    assert relationship is not None
    assert relationship.type == RelationshipType.exact_duplicate
    assert relationship.confidence == 1.0
    # source/target are a canonical (sorted) pair, not an origin direction
    assert {relationship.source_id, relationship.target_id} == {"a", "b"}


def test_reworded_text_is_near_duplicate():
    detector = RuleBasedRelationshipDetector()
    a = _question("a", "A car accelerates uniformly from rest to 20 m/s in 5 seconds.")
    b = _question("b", "A car accelerates uniformly from rest to 20 meters per second in 5 seconds.")

    relationship = detector.detect_pair(a, b)

    assert relationship is not None
    assert relationship.type == RelationshipType.near_duplicate
    assert relationship.confidence >= 0.8


def test_same_question_with_different_numbers_is_variant():
    detector = RuleBasedRelationshipDetector()
    a = _question("a", "A particle of mass 2 kg moves under a force F = 3x N. Find its acceleration at x = 4 m.")
    b = _question("b", "A particle of mass 5 kg moves under a force F = 7x N. Find its acceleration at x = 9 m.")

    relationship = detector.detect_pair(a, b)

    assert relationship is not None
    assert relationship.type == RelationshipType.variant


def test_shared_topic_and_concepts_is_same_concept():
    detector = RuleBasedRelationshipDetector()
    a = _question(
        "a",
        "Two blocks connected by a string over a pulley. Find the tension.",
        subject="Physics",
        topic="Mechanics",
        concepts=["Force", "Tension", "Pulley"],
    )
    b = _question(
        "b",
        "A block slides down a frictionless incline. Find its acceleration.",
        subject="Physics",
        topic="Mechanics",
        concepts=["Force", "Tension", "Friction"],
    )

    relationship = detector.detect_pair(a, b)

    assert relationship is not None
    assert relationship.type == RelationshipType.same_concept


def test_shared_subject_only_is_related():
    detector = RuleBasedRelationshipDetector()
    a = _question(
        "a",
        "Calculate the current flowing through a resistor in a circuit.",
        subject="Physics",
        topic="Electromagnetism",
        concepts=["Current", "Resistor"],
    )
    b = _question(
        "b",
        "A block is projected up a frictionless incline. Find the height reached.",
        subject="Physics",
        topic="Mechanics",
        concepts=["Height"],
    )

    relationship = detector.detect_pair(a, b)

    assert relationship is not None
    assert relationship.type == RelationshipType.related


def test_unrelated_questions_have_no_relationship():
    detector = RuleBasedRelationshipDetector()
    a = _question(
        "a",
        "Define specific heat capacity and give its SI unit.",
        subject="Physics",
        topic="Thermodynamics",
        concepts=["Heat"],
    )
    b = _question(
        "b",
        "What is the product of the reaction between D-glucose and nitric acid?",
        subject="Chemistry",
        topic="Organic Chemistry",
        concepts=["Oxidation"],
    )

    relationship = detector.detect_pair(a, b)

    assert relationship is None


def test_detection_is_symmetric_regardless_of_argument_order():
    detector = RuleBasedRelationshipDetector()
    a = _question("a", "State and explain Newton's second law of motion.")
    b = _question("b", "state and explain newton's second law of motion.")

    forward = detector.detect_pair(a, b)
    backward = detector.detect_pair(b, a)

    assert forward is not None and backward is not None
    assert forward.relationship_id == backward.relationship_id
    assert forward.type == backward.type
