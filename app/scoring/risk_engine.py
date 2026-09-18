
from datetime import datetime
from typing import Any


# ============================================================
# CONFIGURATION
# ============================================================

# These are prototype investigation-prioritization thresholds.
# They are intentionally deterministic and configurable.
#
# They are NOT production regulatory thresholds.

HIGH_VALUE_THRESHOLD = 10_000.0

STRUCTURING_LOWER_BOUND = 8_000.0
STRUCTURING_UPPER_BOUND = 10_000.0

RAPID_MOVEMENT_MINUTES = 180

# Countries that the prototype treats as unusual/high-risk
# geography signals for investigation prioritization.
#
# This is NOT a regulatory classification.
UNUSUAL_GEOGRAPHIES = {
    "Malaysia",
    "United Arab Emirates",
}


# Signal weights
HIGH_VALUE_WEIGHT = 20
STRUCTURING_WEIGHT = 25
RAPID_MOVEMENT_WEIGHT = 25
UNUSUAL_GEOGRAPHY_WEIGHT = 15
MULTIPLE_TRANSACTIONS_WEIGHT = 10


# Historical feedback adjustments.
#
# These values affect future investigation prioritization only.
# They do NOT change the underlying deterministic risk signals.
FEEDBACK_ADJUSTMENTS = {
    "TRUE HIT": 10.0,
    "FALSE POSITIVE": -10.0,
    "ESCALATED": 5.0,
}


# ============================================================
# HELPERS
# ============================================================

def _parse_timestamp(timestamp: str | datetime) -> datetime:
    """
    Convert a timestamp string or datetime into a datetime object.
    """

    if isinstance(timestamp, datetime):
        return timestamp

    return datetime.fromisoformat(timestamp)


def _normalized_country(country: str | None) -> str:
    """
    Normalize country text for deterministic comparisons.
    """

    if not country:
        return ""

    return country.strip().lower()


def _risk_level(score: float) -> str:
    """
    Convert a numeric score into the prototype risk level.
    """

    if score >= 70:
        return "HIGH"

    if score >= 40:
        return "MEDIUM"

    return "LOW"


# ============================================================
# INDIVIDUAL RISK SIGNALS
# ============================================================

def detect_high_value_transactions(
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Identify transactions whose amount exceeds the configured
    prototype high-value threshold.
    """

    signals = []

    for transaction in transactions:
        amount = float(transaction.get("amount", 0))

        if amount >= HIGH_VALUE_THRESHOLD:
            signals.append(
                {
                    "signal": "HIGH_VALUE_TRANSACTION",
                    "weight": HIGH_VALUE_WEIGHT,
                    "transaction_ids": [
                        transaction["transaction_id"]
                    ],
                    "explanation": (
                        f"Transaction {transaction['transaction_id']} "
                        f"has an amount of "
                        f"{amount:.2f} "
                        f"{transaction.get('currency', '')}, "
                        f"which meets or exceeds the configured "
                        f"high-value threshold of "
                        f"{HIGH_VALUE_THRESHOLD:.2f}."
                    ),
                }
            )

    return signals


def detect_structuring(
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Identify multiple transactions whose amounts fall within
    the configured structuring review band.

    This is a prototype behavioral signal. It does NOT conclude
    that structuring has occurred.
    """

    candidates = []

    for transaction in transactions:
        amount = float(transaction.get("amount", 0))

        if (
            STRUCTURING_LOWER_BOUND
            <= amount
            < STRUCTURING_UPPER_BOUND
        ):
            candidates.append(transaction)

    if len(candidates) < 2:
        return []

    transaction_ids = [
        transaction["transaction_id"]
        for transaction in candidates
    ]

    return [
        {
            "signal": "POSSIBLE_STRUCTURING",
            "weight": STRUCTURING_WEIGHT,
            "transaction_ids": transaction_ids,
            "explanation": (
                f"{len(candidates)} transactions fall within "
                f"the configured review band of "
                f"{STRUCTURING_LOWER_BOUND:.2f} to "
                f"{STRUCTURING_UPPER_BOUND:.2f}. "
                "This is a behavioral indicator for review and "
                "does not by itself establish structuring."
            ),
        }
    ]


def detect_rapid_movement(
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Identify an incoming transaction followed by an outgoing
    transaction within the configured time window.

    Transactions are ordered chronologically before analysis.
    """

    if len(transactions) < 2:
        return []

    ordered_transactions = sorted(
        transactions,
        key=lambda transaction: _parse_timestamp(
            transaction["timestamp"]
        ),
    )

    signals = []

    for index, incoming in enumerate(ordered_transactions):
        incoming_type = (
            incoming.get("transaction_type", "")
            .strip()
            .upper()
        )

        if incoming_type not in {"CREDIT", "INCOMING"}:
            continue

        incoming_time = _parse_timestamp(
            incoming["timestamp"]
        )

        for outgoing in ordered_transactions[index + 1:]:
            outgoing_type = (
                outgoing.get("transaction_type", "")
                .strip()
                .upper()
            )

            if outgoing_type not in {"DEBIT", "OUTGOING"}:
                continue

            outgoing_time = _parse_timestamp(
                outgoing["timestamp"]
            )

            elapsed_minutes = (
                outgoing_time - incoming_time
            ).total_seconds() / 60

            if (
                0 <= elapsed_minutes
                <= RAPID_MOVEMENT_MINUTES
            ):
                signals.append(
                    {
                        "signal": "RAPID_MOVEMENT",
                        "weight": RAPID_MOVEMENT_WEIGHT,
                        "transaction_ids": [
                            incoming["transaction_id"],
                            outgoing["transaction_id"],
                        ],
                        "explanation": (
                            f"Incoming transaction "
                            f"{incoming['transaction_id']} "
                            f"was followed by outgoing "
                            f"transaction "
                            f"{outgoing['transaction_id']} "
                            f"after approximately "
                            f"{elapsed_minutes:.1f} minutes, "
                            f"within the configured "
                            f"{RAPID_MOVEMENT_MINUTES}-minute "
                            "review window."
                        ),
                    }
                )

                # Only report the first qualifying outgoing
                # transaction for each incoming transaction.
                break

    return signals


def detect_unusual_geography(
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Identify transactions involving configured prototype
    unusual/high-risk geography signals.

    This is a prioritization signal, not a regulatory
    determination.
    """

    signals = []

    for transaction in transactions:
        country = transaction.get("country", "")
        normalized = _normalized_country(country)

        configured_country = None

        for candidate in UNUSUAL_GEOGRAPHIES:
            if normalized == candidate.lower():
                configured_country = candidate
                break

        if configured_country:
            signals.append(
                {
                    "signal": "UNUSUAL_GEOGRAPHY",
                    "weight": UNUSUAL_GEOGRAPHY_WEIGHT,
                    "transaction_ids": [
                        transaction["transaction_id"]
                    ],
                    "explanation": (
                        f"Transaction "
                        f"{transaction['transaction_id']} "
                        f"involves {country}, which is included "
                        "in the prototype unusual-geography "
                        "configuration."
                    ),
                }
            )

    return signals


def detect_multiple_transactions(
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Identify cases where multiple transactions are present
    in the investigation set.

    This provides a small contextual signal rather than
    treating transaction count alone as suspicious.
    """

    if len(transactions) < 3:
        return []

    transaction_ids = [
        transaction["transaction_id"]
        for transaction in transactions
    ]

    return [
        {
            "signal": "MULTIPLE_TRANSACTIONS",
            "weight": MULTIPLE_TRANSACTIONS_WEIGHT,
            "transaction_ids": transaction_ids,
            "explanation": (
                f"The investigation set contains "
                f"{len(transactions)} transactions, "
                "providing additional behavioral context "
                "for review."
            ),
        }
    ]


# ============================================================
# MAIN RISK ENGINE
# ============================================================

def calculate_risk(
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate a deterministic prototype AML investigation risk.

    The score is derived entirely from explicit rules.
    No LLM is involved.

    The returned score is the ORIGINAL deterministic risk score.

    Returns:
        {
            "score": int,
            "risk_level": str,
            "signals": [...],
            "transaction_count": int,
            "original_score": int,
            "feedback_adjustment": 0.0,
            "adjusted_score": int,
            "adjusted_risk_level": str,
        }
    """

    if not transactions:
        return {
            "score": 0,
            "risk_level": "LOW",
            "signals": [],
            "transaction_count": 0,
            "original_score": 0,
            "feedback_adjustment": 0.0,
            "adjusted_score": 0,
            "adjusted_risk_level": "LOW",
        }

    signals = []

    signals.extend(
        detect_high_value_transactions(transactions)
    )

    signals.extend(
        detect_structuring(transactions)
    )

    signals.extend(
        detect_rapid_movement(transactions)
    )

    signals.extend(
        detect_unusual_geography(transactions)
    )

    signals.extend(
        detect_multiple_transactions(transactions)
    )

    score = sum(
        signal["weight"]
        for signal in signals
    )

    # Cap the prototype score at 100.
    score = min(score, 100)

    risk_level = _risk_level(score)

    return {
        "score": score,
        "risk_level": risk_level,
        "signals": signals,
        "transaction_count": len(transactions),
        "original_score": score,
        "feedback_adjustment": 0.0,
        "adjusted_score": score,
        "adjusted_risk_level": risk_level,
    }


# ============================================================
# HISTORICAL FEEDBACK / PRIORITIZATION
# ============================================================


def apply_historical_feedback(
    risk_assessment: dict[str, Any],
    feedback_records: list,
) -> dict[str, Any]:
    """
    Apply relevant historical analyst feedback to an existing
    deterministic risk assessment.

    The original deterministic score is preserved in
    ``original_score``.

    For backward compatibility, ``score`` remains the
    feedback-adjusted prioritization score.

    ``adjusted_score`` is an explicit alias of that prioritization
    score.

    Feedback does not change the underlying deterministic signals.
    """

    original_score = float(
        risk_assessment.get(
            "original_score",
            risk_assessment["score"],
        )
    )

    feedback_adjustment = 0.0

    for feedback in feedback_records:
        disposition = (
            feedback.disposition
            if hasattr(feedback, "disposition")
            else feedback.get("disposition")
        )

        normalized_disposition = (
            str(disposition).strip().upper()
        )

        feedback_adjustment += FEEDBACK_ADJUSTMENTS.get(
            normalized_disposition,
            0.0,
        )

    adjusted_score = max(
        0.0,
        min(
            100.0,
            original_score + feedback_adjustment,
        ),
    )

    original_risk_level = _risk_level(
        original_score
    )

    adjusted_risk_level = _risk_level(
        adjusted_score
    )

    result = dict(risk_assessment)

    # ---------------------------------------------------------
    # ORIGINAL DETERMINISTIC ASSESSMENT
    # ---------------------------------------------------------

    result["original_score"] = original_score
    result["original_risk_level"] = original_risk_level
    result["risk_level"] = adjusted_risk_level

    # ---------------------------------------------------------
    # HISTORICAL FEEDBACK
    # ---------------------------------------------------------

    result["feedback_adjustment"] = feedback_adjustment

    # ---------------------------------------------------------
    # FEEDBACK-ADJUSTED PRIORITIZATION
    # ---------------------------------------------------------

    # ``score`` remains adjusted for compatibility with the
    # existing public contract and tests.
    result["score"] = adjusted_score

    result["adjusted_score"] = adjusted_score
    result["adjusted_risk_level"] = adjusted_risk_level

    return result

