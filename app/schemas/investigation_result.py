
from pydantic import BaseModel, Field


class RegulatoryEvidence(BaseModel):
    topic: str

    regulation_id: str | None = None
    title: str | None = None
    jurisdiction: str | None = None
    source: str | None = None
    source_document: str | None = None

    requirement_id: str
    requirement_topic: str | None = None
    requirement_text: str | None = None

    applicability: list[str] = Field(
        default_factory=list
    )


class InvestigationFinding(BaseModel):
    signal_type: str
    signal: str
    explanation: str

    related_requirements: list[str] = Field(
        default_factory=list
    )

    finding: str


class EvidenceSufficiencyResult(BaseModel):
    sufficient: bool

    missing_evidence: list[str] = Field(
        default_factory=list
    )


class InvestigationResult(BaseModel):
    success: bool
    agent: str
    investigation_id: str

    generated_at: str

    regulatory_evidence: list[RegulatoryEvidence] = Field(
        default_factory=list
    )

    findings: list[InvestigationFinding] = Field(
        default_factory=list
    )

    evidence_sufficiency: EvidenceSufficiencyResult

    conclusion: str

    retrieval_errors: list[str] = Field(
        default_factory=list
    )
