from app.feedback.feedback_engine import (
    apply_feedback_adjustment,
    record_feedback,
)


def test_true_hit_feedback_is_recorded():
    result = record_feedback(
        investigation_id="INV-TEST-001",
        user_id="U001",
        disposition="TRUE HIT",
        reason="Analyst confirmed the activity requires escalation.",
        signal="RAPID_MOVEMENT",
    )

    assert result["success"] is True

    feedback = result["feedback"]

    assert feedback["investigation_id"] == "INV-TEST-001"
    assert feedback["user_id"] == "U001"
    assert feedback["disposition"] == "TRUE HIT"
    assert feedback["signal"] == "RAPID_MOVEMENT"
    assert feedback["adjustment"] == 10


def test_false_positive_reduces_future_prioritization():
    result = apply_feedback_adjustment(
        original_score=70,
        disposition="FALSE POSITIVE",
    )

    assert result["success"] is True
    assert result["original_score"] == 70
    assert result["adjustment"] == -10
    assert result["adjusted_score"] == 60
    assert result["adjusted_risk_level"] == "MEDIUM"


def test_escalated_increases_future_prioritization():
    result = apply_feedback_adjustment(
        original_score=60,
        disposition="ESCALATED",
    )

    assert result["success"] is True
    assert result["original_score"] == 60
    assert result["adjustment"] == 5
    assert result["adjusted_score"] == 65
    assert result["adjusted_risk_level"] == "MEDIUM"


def test_score_is_capped_at_100():
    result = apply_feedback_adjustment(
        original_score=98,
        disposition="TRUE HIT",
    )

    assert result["adjusted_score"] == 100


def test_score_cannot_go_below_zero():
    result = apply_feedback_adjustment(
        original_score=5,
        disposition="FALSE POSITIVE",
    )

    assert result["adjusted_score"] == 0


def test_invalid_disposition_is_rejected():
    result = record_feedback(
        investigation_id="INV-TEST-002",
        user_id="U001",
        disposition="INVALID",
        reason="Invalid disposition test.",
    )

    assert result["success"] is False
    assert "Invalid disposition" in result["error"]


def test_empty_reason_is_rejected():
    result = record_feedback(
        investigation_id="INV-TEST-003",
        user_id="U001",
        disposition="TRUE HIT",
        reason="   ",
    )

    assert result["success"] is False
    assert result["error"] == "Feedback reason is required."


def test_original_score_is_preserved():
    original_score = 72

    result = apply_feedback_adjustment(
        original_score=original_score,
        disposition="FALSE POSITIVE",
    )

    assert original_score == 72
    assert result["original_score"] == 72
