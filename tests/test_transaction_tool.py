from app.auth.context import UserContext
from app.auth.permissions import Role
from app.db import SessionLocal
from app.tools.investigation_tools import get_transaction


def test_cco_can_get_transaction():
    db = SessionLocal()

    try:
        result = get_transaction(
            db=db,
            user=UserContext(
                user_id="CCO-001",
                role=Role.CCO,
            ),
            transaction_id="TXN1042",
        )

        assert result["success"] is True
        assert result["data"]["transaction_id"] == "TXN1042"
        assert result["data"]["customer_id"] == "C102"
        assert result["data"]["amount"] == 9800.0

    finally:
        db.close()


def test_aml_analyst_can_get_transaction():
    db = SessionLocal()

    try:
        result = get_transaction(
            db=db,
            user=UserContext(
                user_id="AML-001",
                role=Role.AML_ANALYST,
            ),
            transaction_id="TXN1042",
        )

        assert result["success"] is True
        assert result["data"]["transaction_id"] == "TXN1042"

    finally:
        db.close()


def test_external_auditor_cannot_get_transaction():
    db = SessionLocal()

    try:
        result = get_transaction(
            db=db,
            user=UserContext(
                user_id="AUD-001",
                role=Role.EXTERNAL_AUDITOR,
            ),
            transaction_id="TXN1042",
        )

        assert result["success"] is False
        assert result["error"] == "ACCESS_DENIED"

    finally:
        db.close()


def test_missing_transaction_returns_not_found():
    db = SessionLocal()

    try:
        result = get_transaction(
            db=db,
            user=UserContext(
                user_id="CCO-001",
                role=Role.CCO,
            ),
            transaction_id="TXN_DOES_NOT_EXIST",
        )

        assert result["success"] is False
        assert result["error"] == "NOT_FOUND"

    finally:
        db.close()


def test_relationship_manager_can_access_transaction_in_assigned_portfolio():
    db = SessionLocal()

    try:
        result = get_transaction(
            db=db,
            user=UserContext(
                user_id="RM-001",
                role=Role.RELATIONSHIP_MANAGER,
                portfolio_id="PORT-002",
            ),
            transaction_id="TXN1042",
        )

        assert result["success"] is True
        assert result["data"]["transaction_id"] == "TXN1042"

    finally:
        db.close()


def test_relationship_manager_cannot_access_transaction_outside_assigned_portfolio():
    db = SessionLocal()

    try:
        result = get_transaction(
            db=db,
            user=UserContext(
                user_id="RM-001",
                role=Role.RELATIONSHIP_MANAGER,
                portfolio_id="PORT-001",
            ),
            transaction_id="TXN1042",
        )

        assert result["success"] is False
        assert result["error"] == "ACCESS_DENIED"

    finally:
        db.close()