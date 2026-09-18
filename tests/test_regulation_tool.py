import pytest

from app.auth.context import UserContext
from app.auth.permissions import Role
from app.tools.investigation_tools import search_regulations


def test_analyst_can_search_regulations():
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    result = search_regulations(user, "structuring")

    assert result["success"] is True
    assert result["query"] == "structuring"
    assert result["match_count"] >= 1

    matches = result["matches"]

    assert any(
        match["requirement_id"] == "AML-PROTOTYPE-001-R2"
        for match in matches
    )


def test_regulation_search_is_case_insensitive():
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    result = search_regulations(user, "STRUCTURING")

    assert result["success"] is True
    assert result["match_count"] >= 1


def test_regulation_search_returns_source_metadata():
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    result = search_regulations(user, "structuring")

    match = result["matches"][0]

    assert match["regulation_id"] == "AML-PROTOTYPE-001"
    assert match["source_document"] == "prototype_aml_requirements"
    assert match["requirement_id"] == "AML-PROTOTYPE-001-R2"
    assert match["requirement_topic"] == "Structuring indicators"


def test_regulation_search_requires_topic():
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    result = search_regulations(user, "")

    assert result["success"] is False
    assert "required" in result["error"].lower()


def test_regulation_search_handles_no_match():
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    result = search_regulations(user, "something_that_does_not_exist")

    assert result["success"] is True
    assert result["match_count"] == 0
    assert result["matches"] == []


def test_regulation_search_authorization_is_enforced():
    user = UserContext(
        user_id="U001",
        role=Role.EXTERNAL_AUDITOR,
    )

    result = search_regulations(user, "structuring")

    assert result["success"] is False
    assert "authorized" in result["error"].lower()