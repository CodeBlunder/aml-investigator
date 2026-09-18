from app.auth.context import UserContext
from app.auth.permissions import Role
from app.db import SessionLocal
from app.tools.investigation_tools import get_alert


def test_cco_can_get_alert():
    db = SessionLocal()

    try:
        result = get_alert(
            db=db,
            user=UserContext(
                user_id="CCO-001",
                role=Role.CCO,
            ),
            alert_id="ALT-102",
        )

        assert result["success"] is True
        assert result["data"]["alert_id"] == "ALT-102"
        assert result["data"]["customer_id"] == "C102"
        assert result["data"]["transaction_id"] == "TXN1042"
        assert result["data"]["severity"] == "HIGH"

    finally:
        db.close()


def test_aml_analyst_can_get_alert():
    db = SessionLocal()

    try:
        result = get_alert(
            db=db,
            user=UserContext(
                user_id="AML-001",
                role=Role.AML_ANALYST,
            ),
            alert_id="ALT-102",
        )

        assert result["success"] is True
        assert result["data"]["alert_id"] == "ALT-102"

    finally:
        db.close()


def test_external_auditor_cannot_get_alert():
    db = SessionLocal()

    try:
        result = get_alert(
            db=db,
            user=UserContext(
                user_id="AUD-001",
                role=Role.EXTERNAL_AUDITOR,
            ),
            alert_id="ALT-102",
        )

        assert result["success"] is False
        assert result["error"] == "ACCESS_DENIED"

    finally:
        db.close()


def test_relationship_manager_can_get_alert_in_assigned_portfolio():
    db = SessionLocal()

    try:
        result = get_alert(
            db=db,
            user=UserContext(
                user_id="RM-001",
                role=Role.RELATIONSHIP_MANAGER,
                portfolio_id="PORT-002",
            ),
            alert_id="ALT-102",
        )

        assert result["success"] is True
        assert result["data"]["alert_id"] == "ALT-102"

    finally:
        db.close()


def test_relationship_manager_cannot_get_alert_outside_portfolio():
    db = SessionLocal()

    try:
        result = get_alert(
            db=db,
            user=UserContext(
                user_id="RM-001",
                role=Role.RELATIONSHIP_MANAGER,
                portfolio_id="PORT-001",
            ),
            alert_id="ALT-102",
        )

        assert result["success"] is False
        assert result["error"] == "ACCESS_DENIED"

    finally:
        db.close()


def test_missing_alert_returns_not_found():
    db = SessionLocal()

    try:
        result = get_alert(
            db=db,
            user=UserContext(
                user_id="CCO-001",
                role=Role.CCO,
            ),
            alert_id="ALERT_DOES_NOT_EXIST",
        )

        assert result["success"] is False
        assert result["error"] == "NOT_FOUND"

    finally:
        db.close()
