from app.agents.screening_agent import ScreeningAgent
from app.auth.context import UserContext
from app.auth.permissions import Role
from app.db import SessionLocal


def get_db():
    return SessionLocal()


def test_screening_agent_builds_golden_case_package():
    db = get_db()

    try:
        agent = ScreeningAgent(db)

        user = UserContext(
            user_id="user-001",
            role=Role.CCO,
        )

        package = agent.investigate(
            user=user,
            customer_id="C102",
            transaction_id="TXN1042",
            alert_id="ALT-102",
            sanctions_query="Arjun Mehta",
        )

        assert package.investigation_id.startswith("INV-")

        assert package.customer is not None
        assert package.customer.customer_id == "C102"

        assert package.alert is not None
        assert package.alert.alert_id == "ALT-102"

        transaction_ids = {
            transaction.transaction_id
            for transaction in package.transactions
        }

        assert {
            "TXN1042",
            "TXN1043",
            "TXN1047",
        }.issubset(transaction_ids)

        assert package.sanctions is not None
        assert package.sanctions.match_count >= 1

        assert (
            package.sanctions.matches[0].match_type
            == "PROBABLE"
        )

        assert package.risk_assessment is not None
        assert package.risk_assessment.risk_level == "HIGH"

        signal_names = {
            signal.signal
            for signal in package.risk_assessment.signals
        }

        assert "HIGH_VALUE_TRANSACTION" in signal_names
        assert "POSSIBLE_STRUCTURING" in signal_names
        assert "RAPID_MOVEMENT" in signal_names
        assert "UNUSUAL_GEOGRAPHY" in signal_names
        assert "MULTIPLE_TRANSACTIONS" in signal_names

        assert package.evidence_sufficiency.sufficient is True
        assert package.evidence_sufficiency.missing_evidence == []

    finally:
        db.close()


def test_screening_agent_respects_relationship_manager_scope():
    db = get_db()

    try:
        agent = ScreeningAgent(db)

        user = UserContext(
            user_id="rm-001",
            role=Role.RELATIONSHIP_MANAGER,
            portfolio_id="PORT-002",
        )

        package = agent.investigate(
            user=user,
            customer_id="C102",
            transaction_id="TXN1042",
            alert_id="ALT-102",
            sanctions_query="Arjun Mehta",
        )

        assert package.customer is not None
        assert package.customer.customer_id == "C102"

        assert package.customer.name != "Arjun Mehta"

        transaction_ids = {
            transaction.transaction_id
            for transaction in package.transactions
        }

        assert "TXN1042" in transaction_ids

        assert package.evidence_sufficiency.sufficient is True

    finally:
        db.close()


def test_screening_agent_denies_relationship_manager_wrong_portfolio():
    db = get_db()

    try:
        agent = ScreeningAgent(db)

        user = UserContext(
            user_id="rm-002",
            role=Role.RELATIONSHIP_MANAGER,
            portfolio_id="PORT-001",
        )

        package = agent.investigate(
            user=user,
            customer_id="C102",
            transaction_id="TXN1042",
            alert_id="ALT-102",
            sanctions_query="Arjun Mehta",
        )

        assert package.customer is None
        assert package.alert is None
        assert package.transactions == []

        assert package.evidence_sufficiency.sufficient is False

        assert (
            "customer_profile"
            in package.evidence_sufficiency.missing_evidence
        )

        assert (
            "primary_transaction"
            in package.evidence_sufficiency.missing_evidence
        )

    finally:
        db.close()


def test_screening_agent_can_recover_customer_from_transaction():
    db = get_db()

    try:
        agent = ScreeningAgent(db)

        user = UserContext(
            user_id="analyst-001",
            role=Role.AML_ANALYST,
        )

        package = agent.investigate(
            user=user,
            transaction_id="TXN1042",
            sanctions_query="Arjun Mehta",
        )

        assert package.transactions

        transaction_ids = {
            transaction.transaction_id
            for transaction in package.transactions
        }

        assert "TXN1042" in transaction_ids

        assert package.risk_assessment is not None

        assert package.sanctions is not None

    finally:
        db.close()


def test_screening_agent_reports_insufficient_evidence():
    db = get_db()

    try:
        agent = ScreeningAgent(db)

        user = UserContext(
            user_id="analyst-002",
            role=Role.AML_ANALYST,
        )

        package = agent.investigate(
            user=user,
            transaction_id="DOES-NOT-EXIST",
        )

        assert package.transactions == []
        assert package.evidence_sufficiency.sufficient is False

        missing = package.evidence_sufficiency.missing_evidence

        assert "primary_transaction" in missing
        assert "transaction_evidence" in missing
        assert "sanctions_screening" in missing
        assert "risk_assessment" in missing

    finally:
        db.close()