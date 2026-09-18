from app.agents.investigation_graph import investigation_graph
from app.auth.context import UserContext
from app.auth.permissions import Role


def test_graph_requires_authenticated_user():
    result = investigation_graph.invoke(
        {
            "query": "Investigate TXN1042",
        }
    )

    assert result["authorized"] is False
    assert result["authorization_error"] is not None
    assert result["investigation_result"] is None


def test_graph_allows_authorized_analyst():
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    result = investigation_graph.invoke(
        {
            "user": user,
            "query": "Why was TXN1042 flagged?",
        }
    )

    assert result["authorized"] is True
    assert result["screening_result"] is not None
    assert result["investigation_package"] is not None


def test_graph_passes_screening_handoff_to_investigation():
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    result = investigation_graph.invoke(
        {
            "user": user,
            "query": "Why was TXN1042 flagged?",
        }
    )

    assert result["handoff_valid"] is True
    assert result["investigation_result"] is not None
    assert result["investigation_result"]["success"] is True


def test_graph_produces_evidence_sufficiency_result():
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    result = investigation_graph.invoke(
        {
            "user": user,
            "query": "Investigate TXN1042",
        }
    )

    investigation_result = result["investigation_result"]

    assert investigation_result is not None
    assert "evidence_sufficiency" in investigation_result
    assert "sufficient" in investigation_result["evidence_sufficiency"]