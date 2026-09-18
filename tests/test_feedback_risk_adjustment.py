from app.scoring.risk_engine import apply_historical_feedback


def test_no_feedback_keeps_original_score():
    assessment = {
        "score": 65,
        "risk_level": "MEDIUM",
        "transaction_count": 3,
        "signals": [],
    }

    result = apply_historical_feedback(assessment, [])

    assert result["original_score"] == 65
    assert result["feedback_adjustment"] == 0
    assert result["score"] == 65
    assert result["risk_level"] == "MEDIUM"


def test_true_hit_increases_score():
    assessment = {
        "score": 65,
        "risk_level": "MEDIUM",
        "transaction_count": 3,
        "signals": [],
    }

    feedback = [
        {"disposition": "TRUE HIT"},
    ]

    result = apply_historical_feedback(assessment, feedback)

    assert result["original_score"] == 65
    assert result["feedback_adjustment"] == 10
    assert result["score"] == 75
    assert result["risk_level"] == "HIGH"


def test_escalated_increases_score():
    assessment = {
        "score": 60,
        "risk_level": "MEDIUM",
        "transaction_count": 2,
        "signals": [],
    }

    feedback = [
        {"disposition": "ESCALATED"},
    ]

    result = apply_historical_feedback(assessment, feedback)

    assert result["original_score"] == 60
    assert result["feedback_adjustment"] == 5
    assert result["score"] == 65
    assert result["risk_level"] == "MEDIUM"


def test_false_positive_decreases_score():
    assessment = {
        "score": 70,
        "risk_level": "HIGH",
        "transaction_count": 4,
        "signals": [],
    }

    feedback = [
        {"disposition": "FALSE POSITIVE"},
    ]

    result = apply_historical_feedback(assessment, feedback)

    assert result["original_score"] == 70
    assert result["feedback_adjustment"] == -10
    assert result["score"] == 60
    assert result["risk_level"] == "MEDIUM"


def test_multiple_feedback_records_are_combined():
    assessment = {
        "score": 60,
        "risk_level": "MEDIUM",
        "transaction_count": 3,
        "signals": [],
    }

    feedback = [
        {"disposition": "TRUE HIT"},
        {"disposition": "ESCALATED"},
        {"disposition": "FALSE POSITIVE"},
    ]

    result = apply_historical_feedback(assessment, feedback)

    assert result["original_score"] == 60
    assert result["feedback_adjustment"] == 5
    assert result["score"] == 65


def test_score_is_capped_at_100():
    assessment = {
        "score": 95,
        "risk_level": "HIGH",
        "transaction_count": 5,
        "signals": [],
    }

    feedback = [
        {"disposition": "TRUE HIT"},
        {"disposition": "TRUE HIT"},
    ]

    result = apply_historical_feedback(assessment, feedback)

    assert result["original_score"] == 95
    assert result["feedback_adjustment"] == 20
    assert result["score"] == 100


def test_score_is_floored_at_zero():
    assessment = {
        "score": 5,
        "risk_level": "LOW",
        "transaction_count": 1,
        "signals": [],
    }

    feedback = [
        {"disposition": "FALSE POSITIVE"},
    ]

    result = apply_historical_feedback(assessment, feedback)

    assert result["original_score"] == 5
    assert result["feedback_adjustment"] == -10
    assert result["score"] == 0
    assert result["risk_level"] == "LOW"


def test_original_assessment_is_not_mutated():
    assessment = {
        "score": 65,
        "risk_level": "MEDIUM",
        "transaction_count": 3,
        "signals": [],
    }

    apply_historical_feedback(
        assessment,
        [{"disposition": "TRUE HIT"}],
    )

    assert assessment["score"] == 65
    assert assessment["risk_level"] == "MEDIUM"


def test_unknown_disposition_has_no_adjustment():
    assessment = {
        "score": 65,
        "risk_level": "MEDIUM",
        "transaction_count": 3,
        "signals": [],
    }

    feedback = [
        {"disposition": "UNKNOWN"},
    ]

    result = apply_historical_feedback(assessment, feedback)

    assert result["feedback_adjustment"] == 0
    assert result["score"] == 65