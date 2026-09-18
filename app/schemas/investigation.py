from typing import Any

from pydantic import BaseModel, Field


# ============================================================
# TRANSACTION EVIDENCE
# ============================================================

class TransactionEvidence(BaseModel):
    """
    Controlled transaction representation passed into an
    investigation.
    """

    transaction_id: str
    customer_id: str
    account_id: str
    timestamp: str | None = None
    transaction_type: str
    amount: float
    currency: str
    counterparty: str
    country: str
    description: str | None = None


# ============================================================
# CUSTOMER EVIDENCE
# ============================================================

class CustomerEvidence(BaseModel):
    """
    Customer information returned by the controlled customer
    tool.

    The name may be masked depending on the user's role.
    """

    customer_id: str
    name: str
    account_id: str
    country: str
    occupation: str | None = None
    business_type: str | None = None
    risk_rating: str
    portfolio_id: str
    kyc_status: str


# ============================================================
# ALERT EVIDENCE
# ============================================================

class AlertEvidence(BaseModel):
    """
    Controlled AML alert representation.
    """

    alert_id: str
    customer_id: str
    transaction_id: str | None = None
    alert_type: str
    severity: str
    status: str
    created_at: str | None = None
    description: str | None = None


# ============================================================
# SANCTIONS EVIDENCE
# ============================================================

class SanctionsMatch(BaseModel):
    """
    A single sanctions/watchlist search result.

    match_type is preserved exactly so that PROBABLE and EXACT
    matches are never conflated.
    """

    entity_id: str
    name: str
    aliases: str | None = None
    country: str
    list_name: str
    match_type: str
    risk_level: str
    matched_on: str


class SanctionsEvidence(BaseModel):
    """
    Controlled sanctions search results.
    """

    query: str
    match_count: int
    matches: list[SanctionsMatch] = Field(
        default_factory=list
    )


# ============================================================
# RISK SIGNAL
# ============================================================

class RiskSignal(BaseModel):
    """
    One deterministic risk signal produced by the risk engine.
    """

    signal: str
    weight: int
    transaction_ids: list[str] = Field(
        default_factory=list
    )
    explanation: str


# ============================================================
# RISK ASSESSMENT
# ============================================================

class RiskAssessment(BaseModel):
    """
    Deterministic prototype risk assessment.

    The score is explainable through the individual signals.
    """

    score: float = Field(ge=0, le=100)
    risk_level: str
    transaction_count: int = Field(ge=0)
    signals: list[RiskSignal]
    original_score: float | None = None
    feedback_adjustment: float = 0.0


# ============================================================
# EVIDENCE SUFFICIENCY
# ============================================================

class EvidenceSufficiency(BaseModel):
    """
    Explicit representation of whether enough evidence is
    available for the next investigation stage.
    """

    sufficient: bool
    missing_evidence: list[str] = Field(
        default_factory=list
    )
    notes: str | None = None


# ============================================================
# INVESTIGATION PACKAGE
# ============================================================

class InvestigationPackage(BaseModel):
    """
    Structured handoff from controlled retrieval/risk logic
    to the Screening Agent.

    This is the primary contract between deterministic tools
    and agent reasoning.
    """

    investigation_id: str

    customer: CustomerEvidence | None = None

    alert: AlertEvidence | None = None

    transactions: list[TransactionEvidence] = Field(
        default_factory=list
    )

    sanctions: SanctionsEvidence | None = None

    risk_assessment: RiskAssessment | None = None
    original_score: float | None = None
    feedback_adjustment: float = 0.0

    evidence_sufficiency: EvidenceSufficiency

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )