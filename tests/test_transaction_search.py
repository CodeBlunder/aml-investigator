from datetime import datetime

from app.auth.context import UserContext
from app.auth.permissions import Role
from app.db import SessionLocal
from app.tools.investigation_tools import search_transactions


def test_aml_analyst_can_search_customer_transactions():
    db = SessionLocal()

    try:
        result = search_transactions(
            db=db,
            user=UserContext(
                user_id="AML-001",
                role=Role.AML_ANALYST,
            ),
            customer_id="C102",
        )

        assert result["success"] is True
        assert result["count"] >= 3

        transaction_ids = {
            transaction["transaction_id"]
            for transaction in result["transactions"]
        }

        assert "TXN1042" in transaction_ids
        assert "TXN1043" in transaction_ids
        assert "TXN1047" in transaction_ids

    finally:
        db.close()


def test_search_can_filter_by_account():
    db = SessionLocal()

    try:
        result = search_transactions(
            db=db,
            user=UserContext(
                user_id="AML-001",
                role=Role.AML_ANALYST,
            ),
            account_id="ACC0102",
        )

        assert result["success"] is True

        for transaction in result["transactions"]:
            assert transaction["account_id"] == "ACC0102"

    finally:
        db.close()


def test_search_can_filter_by_country():
    db = SessionLocal()

    try:
        result = search_transactions(
            db=db,
            user=UserContext(
                user_id="AML-001",
                role=Role.AML_ANALYST,
            ),
            customer_id="C102",
            country="UAE",
        )

        assert result["success"] is True

        for transaction in result["transactions"]:
            assert transaction["country"] == "United Arab Emirates"

        transaction_ids = {
            transaction["transaction_id"]
            for transaction in result["transactions"]
        }

        assert "TXN1042" in transaction_ids
        assert "TXN1043" in transaction_ids
        assert "TXN1047" not in transaction_ids

    finally:
        db.close()


def test_search_can_filter_by_transaction_type():
    db = SessionLocal()

    try:
        result = search_transactions(
            db=db,
            user=UserContext(
                user_id="AML-001",
                role=Role.AML_ANALYST,
            ),
            customer_id="C102",
            transaction_type="CREDIT",
        )

        assert result["success"] is True

        for transaction in result["transactions"]:
            assert transaction["transaction_type"] == "CREDIT"

    finally:
        db.close()


def test_search_can_filter_by_date_range():
    db = SessionLocal()

    try:
        result = search_transactions(
            db=db,
            user=UserContext(
                user_id="AML-001",
                role=Role.AML_ANALYST,
            ),
            customer_id="C102",
            start_date=datetime(2025, 6, 15, 9, 0),
            end_date=datetime(2025, 6, 15, 10, 30),
        )

        assert result["success"] is True

        transaction_ids = {
            transaction["transaction_id"]
            for transaction in result["transactions"]
        }

        assert "TXN1042" in transaction_ids
        assert "TXN1043" in transaction_ids
        assert "TXN1047" not in transaction_ids

    finally:
        db.close()


def test_external_auditor_cannot_search_transactions():
    db = SessionLocal()

    try:
        result = search_transactions(
            db=db,
            user=UserContext(
                user_id="AUD-001",
                role=Role.EXTERNAL_AUDITOR,
            ),
            customer_id="C102",
        )

        assert result["success"] is False
        assert result["error"] == "ACCESS_DENIED"

    finally:
        db.close()


def test_relationship_manager_is_limited_to_assigned_portfolio():
    db = SessionLocal()

    try:
        result = search_transactions(
            db=db,
            user=UserContext(
                user_id="RM-001",
                role=Role.RELATIONSHIP_MANAGER,
                portfolio_id="PORT-002",
            ),
            customer_id="C102",
        )

        assert result["success"] is True
        assert result["count"] >= 3

        for transaction in result["transactions"]:
            assert transaction["customer_id"] == "C102"

    finally:
        db.close()


def test_relationship_manager_cannot_access_wrong_portfolio():
    db = SessionLocal()

    try:
        result = search_transactions(
            db=db,
            user=UserContext(
                user_id="RM-001",
                role=Role.RELATIONSHIP_MANAGER,
                portfolio_id="PORT-001",
            ),
            customer_id="C102",
        )

        assert result["success"] is True
        assert result["count"] == 0
        assert result["transactions"] == []

    finally:
        db.close()


def test_search_rejects_invalid_max_results():
    db = SessionLocal()

    try:
        result = search_transactions(
            db=db,
            user=UserContext(
                user_id="AML-001",
                role=Role.AML_ANALYST,
            ),
            customer_id="C102",
            max_results=101,
        )

        assert result["success"] is False
        assert result["error"] == "INVALID_INPUT"

    finally:
        db.close()
