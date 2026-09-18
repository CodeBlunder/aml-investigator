from app.agents.investigation_graph import investigation_graph
from app.auth.context import UserContext
from app.auth.permissions import Role


def test_golden_investigation_runs_end_to_end():
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    result = investigation_graph.invoke(
        {
            "user": user,
            "query": (
                "Why was transaction TXN1042 flagged, "
                "and does it violate any applicable AML requirements?"
            ),
        }
    )

    assert result["authorized"] is True

    screening_result = result["screening_result"]

    assert screening_result is not None
    assert screening_result["success"] is True
    assert screening_result["agent"] == "Screening Agent"

    package = result["investigation_package"]

    assert package is not None
    assert package.investigation_id

    assert result["handoff_valid"] is True

    transaction_ids = {
        transaction.transaction_id
        for transaction in package.transactions
    }

    assert "TXN1042" in transaction_ids
    assert "TXN1043" in transaction_ids
    assert "TXN1047" in transaction_ids

    assert package.risk_assessment is not None
    assert package.risk_assessment.score >= 0
    assert package.risk_assessment.risk_level in {
        "LOW",
        "MEDIUM",
        "HIGH",
    }

    signal_types = {
        signal.signal.upper()
        for signal in package.risk_assessment.signals
    }

    assert "POSSIBLE_STRUCTURING" in signal_types
    assert "RAPID_MOVEMENT" in signal_types

    investigation_result = result["investigation_result"]

    assert investigation_result is not None
    assert investigation_result["success"] is True
    assert investigation_result["agent"] == "Investigation Agent"

    regulatory_evidence = investigation_result[
        "regulatory_evidence"
    ]

    assert regulatory_evidence

    requirement_ids = {
        item["requirement_id"]
        for item in regulatory_evidence
    }

    assert "AML-PROTOTYPE-001-R1" in requirement_ids
    assert "AML-PROTOTYPE-001-R2" in requirement_ids
    assert "AML-PROTOTYPE-001-R3" in requirement_ids

    findings = investigation_result["findings"]

    structuring_findings = [
        finding
        for finding in findings
        if finding["signal_type"] == "possible_structuring"
    ]

    assert len(structuring_findings) == 1

    assert (
        "AML-PROTOTYPE-001-R2"
        in structuring_findings[0]["related_requirements"]
    )

    evidence_sufficiency = investigation_result[
        "evidence_sufficiency"
    ]

    assert evidence_sufficiency["sufficient"] is True
    assert evidence_sufficiency["missing_evidence"] == []

    conclusion = investigation_result["conclusion"].lower()

    assert (
        "does not by itself establish a regulatory violation"
        in conclusion
    )

    audit_event = result["audit_event"]

    assert audit_event is not None
    assert audit_event["event_type"] == "investigation"
    assert audit_event["authorization_decision"] == "ALLOW"
    assert audit_event["outcome"] == "COMPLETED"

    assert (
        audit_event["investigation_id"]
        == package.investigation_id
    )

    assert "AML-PROTOTYPE-001-R2" in (
        audit_event["evidence_references"]
    )
