
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
    risk_rating: str | None = None
    portfolio_id: str | None = None
    kyc_status: str | None = None


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
    matched_on: str | None = None


class SanctionsEvidence(BaseModel):
    """
    Controlled sanctions search results.
    """

    query: str | None = None
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
    Deterministic risk assessment with historical feedback
    information preserved separately.
    """

    # Effective/current risk after historical feedback.
    score: float = Field(
        ge=0,
        le=100,
    )
    risk_level: str

    transaction_count: int

    # Deterministic risk signals.
    signals: list[RiskSignal] = Field(
        default_factory=list
    )

    # Original deterministic risk before historical feedback.
    original_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    original_risk_level: str | None = None

    # Historical analyst feedback adjustment.
    feedback_adjustment: float = 0.0

    # Explicit adjusted risk after historical feedback.
    adjusted_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    adjusted_risk_level: str | None = None


# ============================================================
# EVIDENCE SUFFICIENCY
# ============================================================

class EvidenceSufficiency(BaseModel):
    """
    Indicates whether the available evidence is sufficient
    for reliable investigation.
    """

    sufficient: bool

    missing_evidence: list[str] = Field(
        default_factory=list
    )

    explanation: str | None = None


# ============================================================
# INVESTIGATION PACKAGE
# ============================================================

class InvestigationPackage(BaseModel):
    """
    Structured handoff package produced by the Screening Agent
    and consumed by the Investigation Agent.
    """

    investigation_id: str

    customer: CustomerEvidence | None = None

    alert: AlertEvidence | None = None

    transactions: list[TransactionEvidence] = Field(
        default_factory=list
    )

    sanctions: SanctionsEvidence | None = None

    risk_assessment: RiskAssessment | None = None

    # Preserved for compatibility with the existing package.
    original_score: float | None = None
    feedback_adjustment: float = 0.0

    evidence_sufficiency: EvidenceSufficiency

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    # Optional LLM interpretation.
    #
    # This does not replace deterministic risk scoring or
    # controlled evidence. It contains only the LLM's
    # interpretation of already-authorized screening evidence.
    llm_screening_summary: str | None = None
