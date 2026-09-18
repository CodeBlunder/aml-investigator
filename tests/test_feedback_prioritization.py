
from app.db import SessionLocal
from app.feedback.feedback_engine import (
    calculate_customer_feedback_adjustment,
    calculate_historical_feedback_adjustment,
    calculate_transaction_feedback_adjustment,
    persist_feedback,
)
from app.models_feedback import Feedback


def cleanup_feedback(db, investigation_ids):
    """
    Remove feedback records created by these tests.

    The application uses a persistent SQLite prototype database,
    so tests must explicitly clean up their own records to remain
    repeatable across separate pytest runs.
    """
    (
        db.query(Feedback)
        .filter(
            Feedback.investigation_id.in_(investigation_ids)
        )
        .delete(synchronize_session=False)
    )
    db.commit()


def test_true_hit_increases_future_prioritization():
    db = SessionLocal()

    investigation_ids = {"INV-FB-001"}

    try:
        cleanup_feedback(db, investigation_ids)

        feedback = persist_feedback(
            db,
            investigation_id="INV-FB-001",
            user_id="AML-001",
            customer_id="FB-CUSTOMER-001",
            transaction_id="FB-TXN-001",
            disposition="TRUE HIT",
            reason="Analyst confirmed the risk indicator.",
            signal="POSSIBLE_STRUCTURING",
        )

        result = calculate_historical_feedback_adjustment(
            [feedback]
        )

        assert result["success"] is True
        assert result["feedback_count"] == 1
        assert result["adjustment"] == 10

    finally:
        cleanup_feedback(db, investigation_ids)
        db.close()


def test_false_positive_decreases_future_prioritization():
    db = SessionLocal()

    investigation_ids = {"INV-FB-002"}

    try:
        cleanup_feedback(db, investigation_ids)

        feedback = persist_feedback(
            db,
            investigation_id="INV-FB-002",
            user_id="AML-001",
            customer_id="FB-CUSTOMER-002",
            transaction_id="FB-TXN-002",
            disposition="FALSE POSITIVE",
            reason="Reviewed activity was legitimate.",
            signal="RAPID_MOVEMENT",
        )

        result = calculate_historical_feedback_adjustment(
            [feedback]
        )

        assert result["success"] is True
        assert result["feedback_count"] == 1
        assert result["adjustment"] == -10

    finally:
        cleanup_feedback(db, investigation_ids)
        db.close()


def test_escalated_feedback_increases_future_prioritization():
    db = SessionLocal()

    investigation_ids = {"INV-FB-003"}

    try:
        cleanup_feedback(db, investigation_ids)

        feedback = persist_feedback(
            db,
            investigation_id="INV-FB-003",
            user_id="AML-001",
            customer_id="FB-CUSTOMER-003",
            transaction_id="FB-TXN-003",
            disposition="ESCALATED",
            reason="Requires enhanced compliance review.",
            signal="UNUSUAL_GEOGRAPHY",
        )

        result = calculate_historical_feedback_adjustment(
            [feedback]
        )

        assert result["success"] is True
        assert result["feedback_count"] == 1
        assert result["adjustment"] == 5

    finally:
        cleanup_feedback(db, investigation_ids)
        db.close()


def test_multiple_feedback_records_are_aggregated():
    db = SessionLocal()

    investigation_ids = {
        "INV-FB-004",
        "INV-FB-005",
        "INV-FB-006",
    }

    try:
        cleanup_feedback(db, investigation_ids)

        feedback_one = persist_feedback(
            db,
            investigation_id="INV-FB-004",
            user_id="AML-001",
            customer_id="FB-CUSTOMER-004",
            transaction_id="FB-TXN-004",
            disposition="TRUE HIT",
            reason="Confirmed suspicious pattern.",
        )

        feedback_two = persist_feedback(
            db,
            investigation_id="INV-FB-005",
            user_id="AML-002",
            customer_id="FB-CUSTOMER-004",
            transaction_id="FB-TXN-004",
            disposition="ESCALATED",
            reason="Escalated for further review.",
        )

        feedback_three = persist_feedback(
            db,
            investigation_id="INV-FB-006",
            user_id="AML-003",
            customer_id="FB-CUSTOMER-004",
            transaction_id="FB-TXN-004",
            disposition="FALSE POSITIVE",
            reason=(
                "Later review determined activity "
                "was legitimate."
            ),
        )

        result = calculate_historical_feedback_adjustment(
            [
                feedback_one,
                feedback_two,
                feedback_three,
            ]
        )

        assert result["success"] is True
        assert result["feedback_count"] == 3
        assert result["adjustment"] == 5

    finally:
        cleanup_feedback(db, investigation_ids)
        db.close()


def test_customer_feedback_adjustment_reads_persisted_feedback():
    db = SessionLocal()

    investigation_ids = {"INV-FB-007"}

    try:
        cleanup_feedback(db, investigation_ids)

        persist_feedback(
            db,
            investigation_id="INV-FB-007",
            user_id="AML-001",
            customer_id="FB-CUSTOMER-005",
            transaction_id="FB-TXN-005",
            disposition="TRUE HIT",
            reason="Confirmed risk pattern.",
        )

        result = calculate_customer_feedback_adjustment(
            db,
            "FB-CUSTOMER-005",
        )

        assert result["success"] is True
        assert result["customer_id"] == "FB-CUSTOMER-005"
        assert result["feedback_count"] == 1
        assert result["adjustment"] == 10

    finally:
        cleanup_feedback(db, investigation_ids)
        db.close()


def test_transaction_feedback_adjustment_reads_persisted_feedback():
    db = SessionLocal()

    investigation_ids = {"INV-FB-008"}

    try:
        cleanup_feedback(db, investigation_ids)

        persist_feedback(
            db,
            investigation_id="INV-FB-008",
            user_id="AML-001",
            customer_id="FB-CUSTOMER-006",
            transaction_id="FB-TXN-006",
            disposition="FALSE POSITIVE",
            reason="Activity was verified as legitimate.",
        )

        result = calculate_transaction_feedback_adjustment(
            db,
            "FB-TXN-006",
        )

        assert result["success"] is True
        assert result["transaction_id"] == "FB-TXN-006"
        assert result["feedback_count"] == 1
        assert result["adjustment"] == -10

    finally:
        cleanup_feedback(db, investigation_ids)
        db.close()


def test_customer_without_feedback_has_zero_adjustment():
    db = SessionLocal()

    investigation_ids = set()

    try:
        result = calculate_customer_feedback_adjustment(
            db,
            "FB-CUSTOMER-NO-HISTORY",
        )

        assert result["success"] is True
        assert result["feedback_count"] == 0
        assert result["adjustment"] == 0

    finally:
        cleanup_feedback(db, investigation_ids)
        db.close()
