from datetime import datetime, timezone
from uuid import uuid4

from app.auth.context import UserContext
from app.feedback.repository import FeedbackRepository
from app.scoring.risk_engine import (
    apply_historical_feedback,
    calculate_risk,
)
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
from app.tools.investigation_tools import (
    find_alerts,
    get_alert,
    get_customer,
    get_transaction,
    search_sanctions,
    search_transactions,
)


def _successful_data(result: dict):
    """
    Return the useful payload from a successful tool response.

    Some controlled tools return:
        {"success": True, "data": {...}}

    Other controlled tools return their useful fields at
    the top level:
        {"success": True, "transactions": [...]}
    """

    if not isinstance(result, dict):
        return None

    if result.get("success") is False:
        return None

    if "data" in result:
        return result["data"]

    return result


def _extract_transactions(result: dict) -> list[dict]:
    """
    Extract transactions from the controlled transaction tool.
    """

    data = _successful_data(result)

    if data is None:
        return []

    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    transactions = data.get("transactions")

    if isinstance(transactions, list):
        return transactions

    for key in ("results", "items"):
        value = data.get(key)

        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            nested = value.get("transactions")

            if isinstance(nested, list):
                return nested

    return []

def _extract_alerts(result: dict) -> list[dict]:
    """
    Extract alerts from the controlled alert-search tool.
    """

    data = _successful_data(result)

    if data is None:
        return []

    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    alerts = data.get("alerts")

    if isinstance(alerts, list):
        return alerts

    return []

def _extract_sanctions(result: dict) -> list[dict]:
    """
    Extract sanctions matches from the controlled sanctions tool.
    """

    data = _successful_data(result)

    if data is None:
        return []

    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    matches = data.get("matches")

    if isinstance(matches, list):
        return matches

    for key in ("results", "items"):
        value = data.get(key)

        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            nested = value.get("matches")

            if isinstance(nested, list):
                return nested

    return []


def _transaction_evidence(
    transaction: dict,
) -> TransactionEvidence:
    """
    Convert a controlled transaction result into structured
    transaction evidence.
    """

    return TransactionEvidence(
        transaction_id=transaction["transaction_id"],
        customer_id=transaction["customer_id"],
        account_id=transaction["account_id"],
        timestamp=transaction["timestamp"],
        transaction_type=transaction["transaction_type"],
        amount=transaction["amount"],
        currency=transaction["currency"],
        counterparty=transaction["counterparty"],
        country=transaction["country"],
        description=transaction.get("description"),
    )


def _customer_evidence(
    customer: dict,
) -> CustomerEvidence:
    """
    Convert a controlled customer result into structured
    customer evidence.
    """

    return CustomerEvidence(
        customer_id=customer["customer_id"],
        name=customer["name"],
        account_id=customer["account_id"],
        country=customer["country"],
        occupation=customer["occupation"],
        business_type=customer["business_type"],
        risk_rating=customer["risk_rating"],
        portfolio_id=customer["portfolio_id"],
        kyc_status=customer["kyc_status"],
    )


def _alert_evidence(
    alert: dict,
) -> AlertEvidence:
    """
    Convert a controlled alert result into structured
    alert evidence.
    """

    return AlertEvidence(
        alert_id=alert["alert_id"],
        customer_id=alert["customer_id"],
        transaction_id=alert["transaction_id"],
        alert_type=alert["alert_type"],
        severity=alert["severity"],
        status=alert["status"],
        created_at=alert["created_at"],
        description=alert.get("description"),
    )


def _sanctions_evidence(
    result: dict,
) -> SanctionsEvidence:
    """
    Convert the complete sanctions-tool response into the
    structured sanctions evidence schema.

    The sanctions tool provides:
        query
        match_count
        matches
    """

    data = _successful_data(result)

    if not isinstance(data, dict):
        data = {}

    matches = _extract_sanctions(result)

    return SanctionsEvidence(
        query=data.get("query"),
        match_count=data.get(
            "match_count",
            len(matches),
        ),
        matches=[
            SanctionsMatch(
                entity_id=match["entity_id"],
                name=match["name"],
                aliases=match.get("aliases"),
                country=match["country"],
                list_name=match["list_name"],
                match_type=match["match_type"],
                risk_level=match["risk_level"],
                matched_on=match.get("matched_on"),
            )
            for match in matches
        ],
    )


def _risk_assessment(
    transactions: list[dict],
    feedback_records: list | None = None,
) -> RiskAssessment | None:
    """
    Run the deterministic risk engine and then apply relevant
    historical feedback.

    The original deterministic score is preserved separately
    from the feedback-adjusted score.
    """

    if not transactions:
        return None

    result = calculate_risk(transactions)

    if feedback_records is None:
        feedback_records = []

    result = apply_historical_feedback(
        result,
        feedback_records,
    )

    signals = [
        RiskSignal(
            signal=signal["signal"],
            weight=signal["weight"],
            transaction_ids=signal["transaction_ids"],
            explanation=signal["explanation"],
        )
        for signal in result.get("signals", [])
    ]

    return RiskAssessment(
        score=result["score"],
        risk_level=result["risk_level"],
        signals=signals,
        transaction_count=result["transaction_count"],
        original_score=result.get(
            "original_score",
            result["score"],
        ),
        feedback_adjustment=result.get(
            "feedback_adjustment",
            0.0,
        ),
    )


def _get_relevant_feedback(
    repository: FeedbackRepository,
    customer_id: str | None = None,
    transaction_id: str | None = None,
) -> list:
    """
    Retrieve historical feedback relevant to the current
    investigation.

    Feedback is deduplicated because the same record may match
    both the customer and transaction.
    """

    feedback_records = []
    seen_feedback_ids = set()

    if customer_id:
        records = repository.get_for_customer(customer_id)

        for feedback in records:
            if feedback.id not in seen_feedback_ids:
                feedback_records.append(feedback)
                seen_feedback_ids.add(feedback.id)

    if transaction_id:
        records = repository.get_for_transaction(transaction_id)

        for feedback in records:
            if feedback.id not in seen_feedback_ids:
                feedback_records.append(feedback)
                seen_feedback_ids.add(feedback.id)

    return feedback_records


class ScreeningAgent:
    """
    Screening Agent.

    Responsibilities:
        - retrieve authorized customer information
        - retrieve the primary transaction
        - retrieve related transactions
        - retrieve related alert information
        - perform controlled sanctions screening
        - retrieve relevant historical feedback
        - run the deterministic risk engine
        - apply feedback-based risk prioritization
        - assemble a structured investigation package

    The Screening Agent does not make the final regulatory
    conclusion.
    """

    def __init__(self, db):
        self.db = db

    def investigate(
        self,
        user: UserContext,
        customer_id: str | None = None,
        transaction_id: str | None = None,
        alert_id: str | None = None,
        sanctions_query: str | None = None,
    ) -> InvestigationPackage:

        investigation_id = (
            f"INV-{uuid4().hex[:8].upper()}"
        )

        customer_data = None
        alert_data = None
        primary_transaction_data = None
        transaction_records = []
        sanctions_result = None
        missing_evidence = []

        # =========================================================
        # 1. PRIMARY TRANSACTION
        # =========================================================

        if transaction_id:
            transaction_result = get_transaction(
                self.db,
                user,
                transaction_id,
            )

            if transaction_result.get("success"):
                primary_transaction_data = _successful_data(
                    transaction_result
                )

                if isinstance(
                    primary_transaction_data,
                    dict,
                ):
                    transaction_records.append(
                        primary_transaction_data
                    )

                    # Recover the customer from the transaction
                    # when customer_id was not supplied.
                    if not customer_id:
                        customer_id = (
                            primary_transaction_data.get(
                                "customer_id"
                            )
                        )

        # =========================================================
        # 2. CUSTOMER
        # =========================================================

        if customer_id:
            customer_result = get_customer(
                self.db,
                user,
                customer_id,
            )

            if customer_result.get("success"):
                customer_data = _successful_data(
                    customer_result
                )
            else:
                # A denied or unavailable customer profile is
                # meaningful evidence insufficiency.
                missing_evidence.append(
                    "customer_profile"
                )

        # =========================================================
        # 3. ALERT
        # =========================================================
        
        if alert_id:
            alert_result = get_alert(
                self.db,
                user,
                alert_id,
            )

            if alert_result.get("success"):
                alert_data = _successful_data(
                    alert_result
                )

        else:
            # Discover alerts from the transaction/customer
            # relationship when the caller did not provide
            # an alert ID.
            alert_search_result = find_alerts(
                self.db,
                user,
                customer_id=customer_id,
                transaction_id=transaction_id,
            )

            alert_matches = _extract_alerts(
                alert_search_result
            )

            if alert_matches:
                alert_data = alert_matches[0]
                alert_id = alert_data.get("alert_id") 
       

        # =========================================================
        # 4. RELATED TRANSACTIONS
        # =========================================================

        resolved_customer_id = customer_id

        if (
            not resolved_customer_id
            and isinstance(
                primary_transaction_data,
                dict,
            )
        ):
            resolved_customer_id = (
                primary_transaction_data.get(
                    "customer_id"
                )
            )

        if resolved_customer_id:
            related_result = search_transactions(
                self.db,
                user,
                customer_id=resolved_customer_id,
                max_results=50,
            )

            related_transactions = _extract_transactions(
                related_result
            )

            seen_transaction_ids = {
                transaction.get("transaction_id")
                for transaction in transaction_records
            }

            for transaction in related_transactions:
                transaction_id_value = transaction.get(
                    "transaction_id"
                )

                if (
                    transaction_id_value
                    not in seen_transaction_ids
                ):
                    transaction_records.append(
                        transaction
                    )

                    seen_transaction_ids.add(
                        transaction_id_value
                    )

        # =========================================================
        # 5. TRANSACTION EVIDENCE
        # =========================================================

        transactions = []

        for transaction in transaction_records:
            try:
                transactions.append(
                    _transaction_evidence(transaction)
                )
            except (KeyError, TypeError):
                # Never fabricate incomplete evidence.
                continue

        # =========================================================
        # 6. SANCTIONS SCREENING
        # =========================================================

        if sanctions_query:
            sanctions_result = search_sanctions(
                self.db,
                user,
                name=sanctions_query,
            )

        if sanctions_result is None:
            missing_evidence.append(
                "sanctions_screening"
            )
        elif not sanctions_result.get("success"):
            missing_evidence.append(
                "sanctions_screening"
            )

        sanctions = None

        if (
            sanctions_result is not None
            and sanctions_result.get("success")
        ):
            sanctions = _sanctions_evidence(
                sanctions_result
            )

        # =========================================================
        # 7. EVIDENCE SUFFICIENCY
        # =========================================================

        if primary_transaction_data is None:
            missing_evidence.append(
                "primary_transaction"
            )

        if not transactions:
            missing_evidence.append(
                "transaction_evidence"
            )

        core_evidence_sufficient = (
            primary_transaction_data is not None
            and bool(transactions)
        )

        # =========================================================
        # 8. HISTORICAL FEEDBACK
        # =========================================================

        feedback_repository = FeedbackRepository(
            self.db
        )

        feedback_records = _get_relevant_feedback(
            feedback_repository,
            customer_id=resolved_customer_id,
            transaction_id=transaction_id,
        )

        # =========================================================
        # 9. RISK ASSESSMENT
        # =========================================================

        risk_assessment = _risk_assessment(
            transaction_records,
            feedback_records=feedback_records,
        )

        if risk_assessment is None:
            missing_evidence.append(
                "risk_assessment"
            )

        evidence_sufficient = (
            core_evidence_sufficient
        )

        # Remove duplicate missing-evidence entries
        # while preserving their order.
        deduplicated_missing = list(
            dict.fromkeys(missing_evidence)
        )

        evidence = EvidenceSufficiency(
            sufficient=evidence_sufficient,
            missing_evidence=deduplicated_missing,
            explanation=(
                "Core transaction evidence is sufficient "
                "for screening."
                if evidence_sufficient
                else (
                    "The available evidence is insufficient "
                    "to complete screening reliably."
                )
            ),
        )

        # =========================================================
        # 10. STRUCTURED CUSTOMER EVIDENCE
        # =========================================================

        customer = None

        if isinstance(customer_data, dict):
            customer = _customer_evidence(
                customer_data
            )

        # =========================================================
        # 11. STRUCTURED ALERT EVIDENCE
        # =========================================================

        alert = None

        if isinstance(alert_data, dict):
            alert = _alert_evidence(
                alert_data
            )

        # =========================================================
        # 12. FINAL SCREENING PACKAGE
        # =========================================================

        return InvestigationPackage(
            investigation_id=investigation_id,
            customer=customer,
            alert=alert,
            transactions=transactions,
            sanctions=sanctions,
            risk_assessment=risk_assessment,
            evidence_sufficiency=evidence,
            metadata={
                "customer_id": resolved_customer_id,
                "transaction_id": transaction_id,
                "alert_id": alert_id,
                "generated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            },
        )
