import logging

from app.agents.investigation_graph import investigation_graph
from app.auth.context import UserContext
from app.auth.permissions import Role


def test_graph_creates_audit_event():
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

    audit_event = result["audit_event"]

    assert audit_event is not None
    assert audit_event["event_type"] == "investigation"
    assert audit_event["user_id"] == "U001"
    assert audit_event["role"] == "AML_ANALYST"
    assert audit_event["authorization_decision"] == "ALLOW"
    assert audit_event["outcome"] == "COMPLETED"


def test_graph_audit_contains_investigation_id():
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

    audit_event = result["audit_event"]
    package = result["investigation_package"]

    assert audit_event["investigation_id"] == (
        package.investigation_id
    )


def test_graph_audit_contains_regulatory_evidence_references():
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

    audit_event = result["audit_event"]

    assert isinstance(
        audit_event["evidence_references"],
        list,
    )


def test_graph_audit_does_not_contain_raw_customer_name():
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

    audit_event = result["audit_event"]

    assert "Arjun Mehta" not in str(audit_event)
