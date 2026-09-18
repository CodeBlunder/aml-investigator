from app.auth.context import UserContext
from app.auth.permissions import Role
from app.db import SessionLocal
from app.tools.investigation_tools import get_customer, mask_name


def test_mask_name():
    assert mask_name("Arjun Mehta") == "A**** M****"
    assert mask_name("John Smith") == "J*** S****"


def test_cco_can_get_full_customer():
    db = SessionLocal()

    try:
        result = get_customer(
            db=db,
            user=UserContext(
                user_id="CCO-001",
                role=Role.CCO,
            ),
            customer_id="C102",
        )

        assert result["success"] is True
        assert result["data"]["customer_id"] == "C102"
        assert result["data"]["name"] == "Arjun Mehta"
        assert result["data"]["account_id"] == "ACC0102"

    finally:
        db.close()


def test_aml_analyst_gets_masked_customer():
    db = SessionLocal()

    try:
        result = get_customer(
            db=db,
            user=UserContext(
                user_id="AML-001",
                role=Role.AML_ANALYST,
            ),
            customer_id="C102",
        )

        assert result["success"] is True
        assert result["data"]["customer_id"] == "C102"
        assert result["data"]["name"] == "A**** M****"
        assert result["data"]["name"] != "Arjun Mehta"

    finally:
        db.close()


def test_relationship_manager_gets_masked_customer():
    db = SessionLocal()

    try:
        result = get_customer(
            db=db,
            user=UserContext(
                user_id="RM-001",
                role=Role.RELATIONSHIP_MANAGER,
                portfolio_id="PORT-002",
            ),
            customer_id="C102",
        )

        assert result["success"] is True
        assert result["data"]["name"] == "A**** M****"

    finally:
        db.close()


def test_relationship_manager_cannot_access_customer_outside_portfolio():
    db = SessionLocal()

    try:
        result = get_customer(
            db=db,
            user=UserContext(
                user_id="RM-001",
                role=Role.RELATIONSHIP_MANAGER,
                portfolio_id="PORT-001",
            ),
            customer_id="C102",
        )

        assert result["success"] is False
        assert result["error"] == "ACCESS_DENIED"

    finally:
        db.close()


def test_external_auditor_cannot_get_customer():
    db = SessionLocal()

    try:
        result = get_customer(
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


def test_missing_customer_returns_not_found():
    db = SessionLocal()

    try:
        result = get_customer(
            db=db,
            user=UserContext(
                user_id="CCO-001",
                role=Role.CCO,
            ),
            customer_id="CUSTOMER_DOES_NOT_EXIST",
        )

        assert result["success"] is False
        assert result["error"] == "NOT_FOUND"

    finally:
        db.close()