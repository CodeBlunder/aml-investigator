
from app.agents.investigation_agent import investigate
from app.auth.context import UserContext
from app.auth.permissions import Role
from app.schemas.investigation import (
    EvidenceSufficiency,
    InvestigationPackage,
    RiskAssessment,
    RiskSignal,
    TransactionEvidence,
)


def build_golden_package():
    return InvestigationPackage(
        investigation_id="INV-TEST-001",
        transactions=[
            TransactionEvidence(
                transaction_id="TXN1042",
                customer_id="C102",
                account_id="ACC0102",
                timestamp="2025-06-15T09:10:00",
                transaction_type="CREDIT",
                amount=9800,
                currency="USD",
                counterparty="CP-OFFSHORE-01",
                country="United Arab Emirates",
                description="International transfer",
            ),
            TransactionEvidence(
                transaction_id="TXN1043",
                customer_id="C102",
                account_id="ACC0102",
                timestamp="2025-06-15T10:05:00",
                transaction_type="CREDIT",
                amount=9700,
                currency="USD",
                counterparty="CP-OFFSHORE-02",
                country="United Arab Emirates",
                description="International transfer",
            ),
            TransactionEvidence(
                transaction_id="TXN1047",
                customer_id="C102",
                account_id="ACC0102",
                timestamp="2025-06-15T11:20:00",
                transaction_type="DEBIT",
                amount=18500,
                currency="USD",
                counterparty="CP-INTL-77",
                country="Singapore",
                description="International transfer",
            ),
        ],
        risk_assessment=RiskAssessment(
            score=80,
            risk_level="HIGH",
            transaction_count=3,
            signals=[
                RiskSignal(
                    signal="possible_structuring",
                    explanation=(
                        "Multiple transactions fall within the "
                        "prototype structuring review band."
                    ),
                    weight=25,
                    transaction_ids=[
                        "TXN1042",
                        "TXN1043",
                    ],
                ),
                RiskSignal(
                    signal="rapid_movement",
                    explanation=(
                        "Incoming funds are followed by an outgoing "
                        "debit within the configured rapid-movement window."
                    ),
                    weight=25,
                    transaction_ids=[
                        "TXN1042",
                        "TXN1043",
                        "TXN1047",
                    ],
                ),
            ],
        ),
        evidence_sufficiency=EvidenceSufficiency(
            sufficient=True,
            missing_evidence=[],
        ),
    )


def test_investigation_agent_builds_regulatory_evidence():
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    package = build_golden_package()

    result = investigate(user, package)

    assert result["success"] is True
    assert result["agent"] == "Investigation Agent"

    regulatory_evidence = result["regulatory_evidence"]

    assert len(regulatory_evidence) >= 1

    requirement_ids = {
        item["requirement_id"]
        for item in regulatory_evidence
    }

    assert "AML-PROTOTYPE-001-R2" in requirement_ids


def test_investigation_agent_maps_structuring_signal():
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    package = build_golden_package()

    result = investigate(user, package)

    findings = result["findings"]

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


def test_investigation_agent_preserves_source_metadata():
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    package = build_golden_package()

    result = investigate(user, package)

    evidence = result["regulatory_evidence"]

    match = next(
        item
        for item in evidence
        if item["requirement_id"] == "AML-PROTOTYPE-001-R2"
    )

    assert match["regulation_id"] == "AML-PROTOTYPE-001"
    assert match["source_document"] == "prototype_aml_requirements"
    assert match["requirement_topic"] == "Structuring indicators"


def test_investigation_agent_does_not_claim_regulatory_violation():
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    package = build_golden_package()

    result = investigate(user, package)

    conclusion = result["conclusion"].lower()

    assert (
        "does not by itself establish a regulatory violation"
        in conclusion
    )


def test_investigation_agent_reports_sufficient_evidence():
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    package = build_golden_package()

    result = investigate(user, package)

    assert result["evidence_sufficiency"]["sufficient"] is True
    assert (
        result["evidence_sufficiency"]["missing_evidence"]
        == []
    )


def test_investigation_agent_handles_missing_regulatory_evidence(
    monkeypatch,
):
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    package = build_golden_package()

    def no_regulatory_results(*args, **kwargs):
        return {
            "success": True,
            "query": "structuring",
            "match_count": 0,
            "matches": [],
        }

    monkeypatch.setattr(
        "app.agents.investigation_agent.search_regulations",
        no_regulatory_results,
    )

    result = investigate(user, package)

    assert result["success"] is True
    assert (
        result["evidence_sufficiency"]["sufficient"]
        is False
    )

    assert (
        "regulatory_evidence"
        in result["evidence_sufficiency"]["missing_evidence"]
    )

    assert "insufficient" in result["conclusion"].lower()


def test_investigation_agent_requires_investigation_package():
    user = UserContext(
        user_id="U001",
        role=Role.AML_ANALYST,
    )

    result = investigate(user, None)

    assert result["success"] is False
    assert "InvestigationPackage" in result["error"]


def test_external_auditor_cannot_use_current_regulatory_tool():
    user = UserContext(
        user_id="U002",
        role=Role.EXTERNAL_AUDITOR,
    )

    package = build_golden_package()

    result = investigate(user, package)

    assert result["success"] is True
    assert result["regulatory_evidence"] == []
    assert (
        result["evidence_sufficiency"]["sufficient"]
        is False
    )
