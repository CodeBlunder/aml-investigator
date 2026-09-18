from pydantic import ValidationError
import pytest

from app.schemas.investigation import (
    AlertEvidence,
    CustomerEvidence,
    EvidenceSufficiency,
    InvestigationPackage,
    RiskAssessment,
    RiskSignal,
    SanctionsEvidence,
    SanctionsMatch,
    TransactionEvidence,
)


def make_transaction(
    transaction_id="TXN1042",
    country="United Arab Emirates",
):
    return TransactionEvidence(
        transaction_id=transaction_id,
        customer_id="C102",
        account_id="ACC0102",
        timestamp="2025-06-15T09:10:00",
        transaction_type="CREDIT",
        amount=9800,
        currency="USD",
        counterparty="CP-OFFSHORE-01",
        country=country,
        description="Incoming international transfer",
    )


def make_customer():
    return CustomerEvidence(
        customer_id="C102",
        name="A**** M****",
        account_id="ACC0102",
        country="India",
        occupation="Business Owner",
        business_type="Import Export",
        risk_rating="HIGH",
        portfolio_id="PORT-002",
        kyc_status="VERIFIED",
    )


def make_alert():
    return AlertEvidence(
        alert_id="ALT-102",
        customer_id="C102",
        transaction_id="TXN1042",
        alert_type="SUSPICIOUS_TRANSACTION_PATTERN",
        severity="HIGH",
        status="OPEN",
        created_at="2025-06-15T12:00:00",
        description="Multiple international transactions.",
    )


def make_sanctions():
    return SanctionsEvidence(
        query="Arjun Mehta",
        match_count=1,
        matches=[
            SanctionsMatch(
                entity_id="SAN-001",
                name="Arjun Mehta Trading LLC",
                aliases="AM Trading",
                country="United Arab Emirates",
                list_name="Synthetic Watchlist",
                match_type="PROBABLE",
                risk_level="HIGH",
                matched_on="name_partial",
            )
        ],
    )


def make_risk_assessment():
    return RiskAssessment(
        score=80,
        risk_level="HIGH",
        signals=[
            RiskSignal(
                signal="POSSIBLE_STRUCTURING",
                weight=25,
                transaction_ids=[
                    "TXN1042",
                    "TXN1043",
                ],
                explanation=(
                    "Multiple transactions fall within "
                    "the configured review band."
                ),
            ),
            RiskSignal(
                signal="RAPID_MOVEMENT",
                weight=25,
                transaction_ids=[
                    "TXN1042",
                    "TXN1047",
                ],
                explanation=(
                    "Incoming funds were followed by "
                    "outgoing funds within the review window."
                ),
            ),
        ],
        transaction_count=3,
    )


def make_package():
    return InvestigationPackage(
        investigation_id="INV-0001",
        customer=make_customer(),
        alert=make_alert(),
        transactions=[
            make_transaction("TXN1042"),
            make_transaction("TXN1043"),
            make_transaction(
                "TXN1047",
                "Singapore",
            ),
        ],
        sanctions=make_sanctions(),
        risk_assessment=make_risk_assessment(),
        evidence_sufficiency=EvidenceSufficiency(
            sufficient=True,
            missing_evidence=[],
            notes="Required investigation evidence is available.",
        ),
        metadata={
            "source": "controlled_investigation_tools",
            "prototype": True,
        },
    )


def test_transaction_evidence_schema():
    transaction = make_transaction()

    assert transaction.transaction_id == "TXN1042"
    assert transaction.amount == 9800
    assert transaction.country == "United Arab Emirates"


def test_customer_evidence_supports_masked_name():
    customer = make_customer()

    assert customer.customer_id == "C102"
    assert customer.name == "A**** M****"


def test_alert_evidence_schema():
    alert = make_alert()

    assert alert.alert_id == "ALT-102"
    assert alert.severity == "HIGH"


def test_sanctions_match_preserves_probable_status():
    sanctions = make_sanctions()

    assert sanctions.match_count == 1
    assert sanctions.matches[0].match_type == "PROBABLE"
    assert sanctions.matches[0].risk_level == "HIGH"


def test_risk_assessment_preserves_signals():
    risk = make_risk_assessment()

    assert risk.score == 80
    assert risk.risk_level == "HIGH"
    assert len(risk.signals) == 2

    signal_names = {
        signal.signal
        for signal in risk.signals
    }

    assert "POSSIBLE_STRUCTURING" in signal_names
    assert "RAPID_MOVEMENT" in signal_names


def test_evidence_sufficiency_can_report_missing_evidence():
    evidence = EvidenceSufficiency(
        sufficient=False,
        missing_evidence=[
            "customer_profile",
            "regulatory_evidence",
        ],
        notes="Additional evidence is required.",
    )

    assert evidence.sufficient is False
    assert "customer_profile" in evidence.missing_evidence
    assert "regulatory_evidence" in evidence.missing_evidence


def test_complete_investigation_package():
    package = make_package()

    assert package.investigation_id == "INV-0001"
    assert package.customer.customer_id == "C102"
    assert package.alert.alert_id == "ALT-102"
    assert len(package.transactions) == 3
    assert package.sanctions.match_count == 1
    assert package.risk_assessment.risk_level == "HIGH"
    assert package.evidence_sufficiency.sufficient is True


def test_package_can_exist_with_missing_optional_evidence():
    package = InvestigationPackage(
        investigation_id="INV-0002",
        transactions=[
            make_transaction(),
        ],
        evidence_sufficiency=EvidenceSufficiency(
            sufficient=False,
            missing_evidence=[
                "customer_profile",
                "alert",
                "sanctions_screening",
            ],
        ),
    )

    assert package.customer is None
    assert package.alert is None
    assert package.sanctions is None
    assert package.risk_assessment is None
    assert package.evidence_sufficiency.sufficient is False


def test_risk_score_cannot_exceed_100():
    with pytest.raises(ValidationError):
        RiskAssessment(
            score=101,
            risk_level="HIGH",
            signals=[],
            transaction_count=1,
        )


def test_risk_score_cannot_be_negative():
    with pytest.raises(ValidationError):
        RiskAssessment(
            score=-1,
            risk_level="LOW",
            signals=[],
            transaction_count=1,
        )


def test_transaction_requires_core_fields():
    with pytest.raises(ValidationError):
        TransactionEvidence(
            transaction_id="TXN9999",
        )