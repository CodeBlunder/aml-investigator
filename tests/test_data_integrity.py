
from app.db import SessionLocal
from app.models import (
    Alert,
    Customer,
    SanctionsEntity,
    Transaction,
)


def test_expected_record_counts():
    db = SessionLocal()

    try:
        assert db.query(Customer).count() == 76
        assert db.query(Transaction).count() == 383
        assert db.query(Alert).count() == 21
        assert db.query(SanctionsEntity).count() == 4

    finally:
        db.close()


def test_golden_customer_exists():
    db = SessionLocal()

    try:
        customer = (
            db.query(Customer)
            .filter(Customer.customer_id == "C102")
            .first()
        )

        assert customer is not None
        assert customer.customer_id == "C102"
        assert customer.account_id == "ACC0102"
        assert customer.risk_rating == "HIGH"

    finally:
        db.close()


def test_golden_alert_exists():
    db = SessionLocal()

    try:
        alert = (
            db.query(Alert)
            .filter(Alert.alert_id == "ALT-102")
            .first()
        )

        assert alert is not None
        assert alert.customer_id == "C102"
        assert alert.transaction_id == "TXN1042"
        assert alert.severity == "HIGH"
        assert alert.status == "OPEN"

    finally:
        db.close()


def test_golden_transactions_exist():
    db = SessionLocal()

    try:
        golden_ids = [
            "TXN1042",
            "TXN1043",
            "TXN1047",
        ]

        transactions = (
            db.query(Transaction)
            .filter(Transaction.transaction_id.in_(golden_ids))
            .all()
        )

        assert len(transactions) == 3

        returned_ids = {
            transaction.transaction_id
            for transaction in transactions
        }

        assert returned_ids == set(golden_ids)

        for transaction in transactions:
            assert transaction.customer_id == "C102"
            assert transaction.account_id == "ACC0102"

    finally:
        db.close()


def test_transaction_ids_are_unique():
    db = SessionLocal()

    try:
        transaction_ids = [
            row[0]
            for row in db.query(Transaction.transaction_id).all()
        ]

        assert len(transaction_ids) == len(set(transaction_ids))

    finally:
        db.close()


def test_sanctions_entities_exist():
    db = SessionLocal()

    try:
        entities = db.query(SanctionsEntity).all()

        assert len(entities) == 4

        names = {entity.name for entity in entities}

        assert "Arjun Mehta Trading LLC" in names
        assert "Global Meridian Holdings" in names

    finally:
        db.close()
