
from datetime import datetime, timezone
from typing import Any

from app.models_feedback import Feedback


VALID_DISPOSITIONS = {
    "TRUE HIT",
    "FALSE POSITIVE",
    "ESCALATED",
}


# Prototype adjustment applied to future prioritization.
#
# These values do NOT alter the underlying risk-engine rules and
# do NOT represent regulatory thresholds.
DISPOSITION_ADJUSTMENTS = {
    "TRUE HIT": 10,
    "FALSE POSITIVE": -10,
    "ESCALATED": 5,
}


def record_feedback(
    *,
    investigation_id: str,
    user_id: str,
    disposition: str,
    reason: str,
    signal: str | None = None,
) -> dict[str, Any]:
    """
    Create a structured analyst feedback record.

    Feedback is an input to future investigation prioritization.
    It does not alter the original investigation result.
    """

    normalized_disposition = disposition.strip().upper()

    if normalized_disposition not in VALID_DISPOSITIONS:
        return {
            "success": False,
            "error": (
                f"Invalid disposition '{disposition}'. "
                f"Expected one of: "
                f"{', '.join(sorted(VALID_DISPOSITIONS))}."
            ),
        }

    normalized_reason = reason.strip()

    if not normalized_reason:
        return {
            "success": False,
            "error": "Feedback reason is required.",
        }

    return {
        "success": True,
        "feedback": {
            "investigation_id": investigation_id,
            "user_id": user_id,
            "disposition": normalized_disposition,
            "reason": normalized_reason,
            "signal": signal,
            "adjustment": DISPOSITION_ADJUSTMENTS[
                normalized_disposition
            ],
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
        },
    }


def apply_feedback_adjustment(
    *,
    original_score: int,
    disposition: str,
) -> dict[str, Any]:
    """
    Calculate the prototype prioritization score after feedback.

    The original score is never modified. The returned adjusted score
    is a separate prioritization value.
    """

    normalized_disposition = disposition.strip().upper()

    if normalized_disposition not in VALID_DISPOSITIONS:
        return {
            "success": False,
            "error": f"Invalid disposition '{disposition}'.",
        }

    adjustment = DISPOSITION_ADJUSTMENTS[
        normalized_disposition
    ]

    adjusted_score = max(
        0,
        min(
            100,
            original_score + adjustment,
        ),
    )

    if adjusted_score >= 70:
        adjusted_risk_level = "HIGH"
    elif adjusted_score >= 40:
        adjusted_risk_level = "MEDIUM"
    else:
        adjusted_risk_level = "LOW"

    return {
        "success": True,
        "original_score": original_score,
        "adjustment": adjustment,
        "adjusted_score": adjusted_score,
        "adjusted_risk_level": adjusted_risk_level,
        "disposition": normalized_disposition,
    }


def calculate_historical_feedback_adjustment(
    feedback_records: list[Feedback],
) -> dict[str, Any]:
    """
    Calculate the aggregate prioritization adjustment from
    previously recorded analyst feedback.

    Historical feedback affects future prioritization only.
    It does not change the underlying deterministic risk signals
    or the original risk score.

    Each feedback record contributes its stored adjustment.

    Example:
        TRUE HIT (+10)
        FALSE POSITIVE (-10)

        Net adjustment = 0
    """

    adjustment = 0.0

    for feedback in feedback_records:
        if feedback.disposition not in VALID_DISPOSITIONS:
            continue

        adjustment += float(feedback.adjustment)

    return {
        "success": True,
        "feedback_count": len(feedback_records),
        "adjustment": adjustment,
    }


def calculate_customer_feedback_adjustment(
    db,
    customer_id: str,
) -> dict[str, Any]:
    """
    Retrieve historical feedback for a customer and calculate
    its aggregate effect on future prioritization.
    """

    from app.feedback.repository import FeedbackRepository

    repository = FeedbackRepository(db)

    feedback_records = repository.get_for_customer(
        customer_id
    )

    result = calculate_historical_feedback_adjustment(
        feedback_records
    )

    result["customer_id"] = customer_id

    return result


def calculate_transaction_feedback_adjustment(
    db,
    transaction_id: str,
) -> dict[str, Any]:
    """
    Retrieve historical feedback for a transaction and calculate
    its aggregate effect on future prioritization.
    """

    from app.feedback.repository import FeedbackRepository

    repository = FeedbackRepository(db)

    feedback_records = repository.get_for_transaction(
        transaction_id
    )

    result = calculate_historical_feedback_adjustment(
        feedback_records
    )

    result["transaction_id"] = transaction_id

    return result


def persist_feedback(
    db,
    *,
    investigation_id: str,
    user_id: str,
    customer_id: str | None,
    transaction_id: str | None,
    disposition: str,
    reason: str,
    signal: str | None = None,
):
    """
    Validate and persist analyst feedback.
    """

    result = record_feedback(
        investigation_id=investigation_id,
        user_id=user_id,
        disposition=disposition,
        reason=reason,
        signal=signal,
    )

    if not result.get("success"):
        raise ValueError(result["error"])

    feedback = result["feedback"]

    db_feedback = Feedback(
        investigation_id=feedback["investigation_id"],
        user_id=feedback["user_id"],
        customer_id=customer_id,
        transaction_id=transaction_id,
        signal=feedback["signal"],
        disposition=feedback["disposition"],
        reason=feedback["reason"],
        adjustment=feedback["adjustment"],
        created_at=datetime.fromisoformat(
            feedback["created_at"]
        ),
    )

    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)

    return db_feedback
