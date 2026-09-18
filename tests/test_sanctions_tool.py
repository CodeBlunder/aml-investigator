from app.auth.context import UserContext
from app.auth.permissions import Role
from app.db import SessionLocal
from app.tools.investigation_tools import search_sanctions


def test_cco_can_search_sanctions():
    db = SessionLocal()

    try:
        result = search_sanctions(
            db=db,
            user=UserContext(
                user_id="CCO-001",
                role=Role.CCO,
            ),
            name="Arjun Mehta Trading LLC",
        )

        assert result["success"] is True
        assert result["match_count"] >= 1

        names = [
            match["name"]
            for match in result["matches"]
        ]

        assert "Arjun Mehta Trading LLC" in names

    finally:
        db.close()


def test_aml_analyst_can_search_sanctions():
    db = SessionLocal()

    try:
        result = search_sanctions(
            db=db,
            user=UserContext(
                user_id="AML-001",
                role=Role.AML_ANALYST,
            ),
            name="Global Meridian Holdings",
        )

        assert result["success"] is True
        assert result["match_count"] >= 1

    finally:
        db.close()


def test_external_auditor_cannot_search_sanctions():
    db = SessionLocal()

    try:
        result = search_sanctions(
            db=db,
            user=UserContext(
                user_id="AUD-001",
                role=Role.EXTERNAL_AUDITOR,
            ),
            name="Arjun Mehta",
        )

        assert result["success"] is False
        assert result["error"] == "ACCESS_DENIED"

    finally:
        db.close()


def test_sanctions_search_is_case_insensitive():
    db = SessionLocal()

    try:
        result = search_sanctions(
            db=db,
            user=UserContext(
                user_id="AML-001",
                role=Role.AML_ANALYST,
            ),
            name="arjun mehta trading llc",
        )

        assert result["success"] is True
        assert result["match_count"] >= 1

    finally:
        db.close()


def test_sanctions_search_returns_match_type():
    db = SessionLocal()

    try:
        result = search_sanctions(
            db=db,
            user=UserContext(
                user_id="AML-001",
                role=Role.AML_ANALYST,
            ),
            name="Global Meridian Holdings",
        )

        assert result["success"] is True
        assert result["match_count"] >= 1

        match = result["matches"][0]

        assert match["match_type"] == "EXACT"
        assert match["risk_level"] == "HIGH"

    finally:
        db.close()


def test_sanctions_search_returns_no_match():
    db = SessionLocal()

    try:
        result = search_sanctions(
            db=db,
            user=UserContext(
                user_id="AML-001",
                role=Role.AML_ANALYST,
            ),
            name="Completely Unknown Company",
        )

        assert result["success"] is True
        assert result["match_count"] == 0
        assert result["matches"] == []

    finally:
        db.close()


def test_empty_sanctions_search_is_rejected():
    db = SessionLocal()

    try:
        result = search_sanctions(
            db=db,
            user=UserContext(
                user_id="AML-001",
                role=Role.AML_ANALYST,
            ),
            name="",
        )

        assert result["success"] is False
        assert result["error"] == "INVALID_INPUT"

    finally:
        db.close()
