
from datetime import datetime, timezone

from app.auth.context import UserContext
from app.schemas.investigation import (
    EvidenceSufficiency,
    InvestigationPackage,
)
from app.tools.investigation_tools import search_regulations


def _regulatory_topics(
    package: InvestigationPackage,
) -> list[str]:
    """
    Determine regulatory search topics from Screening Agent
    risk signals and available investigation evidence.
    """

    topics = []

    if package.risk_assessment is None:
        return ["transaction monitoring"]

    for signal in package.risk_assessment.signals:
        signal_text = (
            f"{signal.signal} "
            f"{signal.explanation}"
        ).lower()

        if "structur" in signal_text:
            topics.append("structuring")

        if (
            "rapid" in signal_text
            or "movement" in signal_text
        ):
            topics.append("transaction monitoring")

        if (
            "geograph" in signal_text
            or "country" in signal_text
        ):
            topics.append("unusual geography")

        if "sanction" in signal_text:
            topics.append("sanctions")

    # Any risk signal should also be evaluated against
    # the general transaction-monitoring requirement.
    if package.risk_assessment.signals:
        topics.append("transaction monitoring")

    # If a sanctions match exists, explicitly retrieve
    # the sanctions requirement.
    if (
        package.sanctions is not None
        and package.sanctions.match_count > 0
    ):
        topics.append("sanctions")

    # Alerts should also be evaluated against transaction
    # monitoring requirements.
    if package.alert is not None:
        topics.append("transaction monitoring")

    if not topics:
        topics.append("transaction monitoring")

    return list(dict.fromkeys(topics))


def _build_regulatory_evidence(
    user: UserContext,
    package: InvestigationPackage,
) -> tuple[list[dict], list[str]]:
    """
    Retrieve controlled regulatory evidence for the screening signals.

    Regulatory retrieval is performed through the controlled
    search_regulations tool. The Investigation Agent never performs
    arbitrary database or vector-store access directly.
    """

    evidence = []
    errors = []

    for topic in _regulatory_topics(package):
        try:
            result = search_regulations(user, topic)
        except Exception:
            errors.append(
                f"Regulatory retrieval failed for topic '{topic}'."
            )
            continue

        if not isinstance(result, dict):
            errors.append(
                f"Regulatory retrieval returned an invalid "
                f"response for topic '{topic}'."
            )
            continue

        if result.get("success") is not True:
            errors.append(
                f"Regulatory retrieval failed for topic '{topic}'."
            )
            continue

        matches = result.get("matches", [])

        if not isinstance(matches, list):
            errors.append(
                f"Regulatory retrieval returned invalid matches "
                f"for topic '{topic}'."
            )
            continue

        for match in matches:
            if not isinstance(match, dict):
                continue

            requirement_id = match.get("requirement_id")

            if not requirement_id:
                continue

            evidence.append(
                {
                    "topic": topic,
                    "regulation_id": match.get(
                        "regulation_id"
                    ),
                    "title": match.get("title"),
                    "jurisdiction": match.get(
                        "jurisdiction"
                    ),
                    "source": match.get("source"),
                    "source_document": match.get(
                        "source_document"
                    ),
                    "requirement_id": requirement_id,
                    "requirement_topic": match.get(
                        "requirement_topic"
                    ),
                    "requirement_text": match.get(
                        "requirement_text"
                    ),
                    "applicability": match.get(
                        "applicability",
                        [],
                    ),
                }
            )

    # Deduplicate requirements while preserving
    # the first occurrence and its metadata.
    unique = {}

    for item in evidence:
        requirement_id = item.get("requirement_id")

        if requirement_id:
            unique[requirement_id] = item

    return list(unique.values()), errors


def _determine_evidence_sufficiency(
    package: InvestigationPackage,
    regulatory_evidence: list[dict],
) -> EvidenceSufficiency:
    """
    Determine whether the available screening and regulatory
    evidence is sufficient for a structured investigation finding.

    Sanctions screening is treated as optional enrichment. Its
    absence does not block the investigation when the core
    transaction, risk, and regulatory evidence is available.
    """

    # Screening Agent may report optional evidence gaps.
    # Do not treat the absence of sanctions screening as a
    # hard blocker for the investigation.
    missing = [
        item
        for item in package.evidence_sufficiency.missing_evidence
        if item != "sanctions_screening"
    ]

    if not package.transactions:
        missing.append("transaction_evidence")

    if package.risk_assessment is None:
        missing.append("risk_assessment")
    elif not package.risk_assessment.signals:
        missing.append("risk_signals")

    if not regulatory_evidence:
        missing.append("regulatory_evidence")

    missing = list(dict.fromkeys(missing))

    return EvidenceSufficiency(
        sufficient=len(missing) == 0,
        missing_evidence=missing,
    )


def _build_findings(
    package: InvestigationPackage,
    regulatory_evidence: list[dict],
) -> list[dict]:
    """
    Build evidence-backed findings by matching Screening Agent
    signals to retrieved regulatory requirements.
    """

    findings = []

    if package.risk_assessment is None:
        return findings

    for signal in package.risk_assessment.signals:
        signal_text = (
            f"{signal.signal} "
            f"{signal.explanation}"
        ).lower()

        related = []

        for regulation in regulatory_evidence:
            applicability = [
                str(value).lower()
                for value in regulation.get(
                    "applicability",
                    [],
                )
            ]

            if (
                "structur" in signal_text
                and "structuring" in applicability
            ):
                related.append(regulation)

            elif (
                (
                    "rapid" in signal_text
                    or "movement" in signal_text
                )
                and "transaction_monitoring"
                in applicability
            ):
                related.append(regulation)

            elif (
                (
                    "geograph" in signal_text
                    or "country" in signal_text
                )
                and "unusual_geography"
                in applicability
            ):
                related.append(regulation)

            elif (
                "sanction" in signal_text
                and "sanctions" in applicability
            ):
                related.append(regulation)

            elif "transaction_monitoring" in applicability:
                related.append(regulation)

        requirement_ids = [
            item["requirement_id"]
            for item in related
            if item.get("requirement_id")
        ]

        findings.append(
            {
                "signal_type": signal.signal.lower(),
                "signal": signal.signal,
                "explanation": signal.explanation,
                "related_requirements": (
                    list(dict.fromkeys(requirement_ids))
                ),
                "finding": (
                    "The observed activity is consistent with "
                    "a risk indicator that warrants additional "
                    "review under the retrieved monitoring "
                    "requirements."
                    if related
                    else
                    "The observed risk indicator could not "
                    "be mapped to retrieved regulatory evidence."
                ),
            }
        )

    return findings


def investigate(
    user: UserContext,
    package: InvestigationPackage,
) -> dict:
    """
    Investigation Agent.

    Receives the structured Screening Agent handoff, retrieves
    relevant regulatory evidence through the controlled regulatory
    tool, and produces an evidence-backed finding.

    This prototype does not make a legal determination or claim
    that a transaction violates a regulation.
    """

    # ---------------------------------------------------------
    # 1. VALIDATE HANDOFF
    # ---------------------------------------------------------

    if not isinstance(package, InvestigationPackage):
        return {
            "success": False,
            "error": "InvestigationPackage is required.",
        }

    # ---------------------------------------------------------
    # 2. RETRIEVE REGULATORY EVIDENCE
    # ---------------------------------------------------------

    regulatory_evidence, retrieval_errors = (
        _build_regulatory_evidence(
            user,
            package,
        )
    )

    # ---------------------------------------------------------
    # 3. DETERMINE EVIDENCE SUFFICIENCY
    # ---------------------------------------------------------

    evidence_sufficiency = (
        _determine_evidence_sufficiency(
            package,
            regulatory_evidence,
        )
    )

    # ---------------------------------------------------------
    # 4. BUILD EVIDENCE-BACKED FINDINGS
    # ---------------------------------------------------------

    findings = _build_findings(
        package,
        regulatory_evidence,
    )

    # ---------------------------------------------------------
    # 5. BUILD CONCLUSION
    # ---------------------------------------------------------

    if not evidence_sufficiency.sufficient:
        conclusion = (
            "Evidence is insufficient for a complete "
            "investigation finding. Additional evidence "
            "is required before drawing a stronger "
            "conclusion. The available evidence does not "
            "by itself establish a regulatory violation."
        )

    elif findings:
        conclusion = (
            "The screening evidence contains risk indicators "
            "that correspond to retrieved AML monitoring "
            "requirements. The available evidence supports "
            "additional investigation and review; it does "
            "not by itself establish a regulatory violation."
        )

    else:
        conclusion = (
            "No evidence-backed regulatory finding could "
            "be established from the available investigation "
            "package. The available evidence does not by "
            "itself establish a regulatory violation."
        )

    # ---------------------------------------------------------
    # 6. RETURN CONTROLLED RESULT
    # ---------------------------------------------------------

    return {
        "success": True,
        "agent": "Investigation Agent",
        "investigation_id": package.investigation_id,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "regulatory_evidence": regulatory_evidence,
        "findings": findings,
        "evidence_sufficiency": (
            evidence_sufficiency.model_dump()
        ),
        "conclusion": conclusion,
        "retrieval_errors": retrieval_errors,
    }
