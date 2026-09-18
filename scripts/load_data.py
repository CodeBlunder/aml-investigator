
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.db import SessionLocal
from app.models import (
    Alert,
    Customer,
    SanctionsEntity,
    Transaction,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"


def load_customers(db):
    path = DATA_DIR / "customers" / "customers.csv"
    df = pd.read_csv(path)

    for _, row in df.iterrows():
        customer = Customer(
            customer_id=row["customer_id"],
            name=row["name"],
            account_id=row["account_id"],
            country=row["country"],
            occupation=row["occupation"],
            business_type=row["business_type"],
            risk_rating=row["risk_rating"],
            portfolio_id=row["portfolio_id"],
            kyc_status=row["kyc_status"],
        )

        db.add(customer)

    print(f"Loaded {len(df)} customers")


def load_transactions(db):
    path = DATA_DIR / "transactions" / "transactions.csv"
    df = pd.read_csv(path)

    for _, row in df.iterrows():
        transaction = Transaction(
            transaction_id=row["transaction_id"],
            customer_id=row["customer_id"],
            account_id=row["account_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            transaction_type=row["transaction_type"],
            amount=float(row["amount"]),
            currency=row["currency"],
            counterparty=row["counterparty"],
            country=row["country"],
            description=row["description"],
        )

        db.add(transaction)

    print(f"Loaded {len(df)} transactions")


def load_alerts(db):
    path = DATA_DIR / "alerts" / "alerts.csv"
    df = pd.read_csv(path)

    for _, row in df.iterrows():
        alert = Alert(
            alert_id=row["alert_id"],
            customer_id=row["customer_id"],
            transaction_id=row["transaction_id"],
            alert_type=row["alert_type"],
            severity=row["severity"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            description=row["description"],
        )

        db.add(alert)

    print(f"Loaded {len(df)} alerts")


def load_sanctions(db):
    path = DATA_DIR / "sanctions" / "sanctions.csv"
    df = pd.read_csv(path)

    for _, row in df.iterrows():
        entity = SanctionsEntity(
            entity_id=row["entity_id"],
            name=row["name"],
            aliases=row["aliases"],
            country=row["country"],
            list_name=row["list_name"],
            match_type=row["match_type"],
            risk_level=row["risk_level"],
        )

        db.add(entity)

    print(f"Loaded {len(df)} sanctions entities")


def main():
    print("Loading AML Investigator data into SQLite...")
    print()

    db = SessionLocal()

    try:
        # Clean prototype database before reloading.
        # This makes the synthetic-data loader safe to rerun.
        db.query(Transaction).delete()
        db.query(Alert).delete()
        db.query(Customer).delete()
        db.query(SanctionsEntity).delete()

        db.commit()

        print("Existing data cleared.")
        print()

        load_customers(db)
        load_transactions(db)
        load_alerts(db)
        load_sanctions(db)

        db.commit()

        print()
        print("Data loading complete.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()

