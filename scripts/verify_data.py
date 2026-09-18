
from app.db import SessionLocal
from app.models import Customer, Transaction, Alert, SanctionsEntity


def main():
    db = SessionLocal()

    try:
        print("=" * 60)
        print("AML INVESTIGATOR DATABASE VERIFICATION")
        print("=" * 60)

        # -------------------------------------------------
        # Record counts
        # -------------------------------------------------

        customer_count = db.query(Customer).count()
        transaction_count = db.query(Transaction).count()
        alert_count = db.query(Alert).count()
        sanctions_count = db.query(SanctionsEntity).count()

        print("\nRecord counts:")
        print(f"  Customers:   {customer_count}")
        print(f"  Transactions:{transaction_count}")
        print(f"  Alerts:      {alert_count}")
        print(f"  Sanctions:   {sanctions_count}")

        # -------------------------------------------------
        # Golden customer
        # -------------------------------------------------

        customer = (
            db.query(Customer)
            .filter(Customer.customer_id == "C102")
            .first()
        )

        print("\nGolden customer:")
        if customer:
            print(f"  ID:           {customer.customer_id}")
            print(f"  Name:         {customer.name}")
            print(f"  Account:      {customer.account_id}")
            print(f"  Risk rating:  {customer.risk_rating}")
            print(f"  Portfolio:    {customer.portfolio_id}")
        else:
            print("  ERROR: C102 not found")

        # -------------------------------------------------
        # Golden alert
        # -------------------------------------------------

        alert = (
            db.query(Alert)
            .filter(Alert.alert_id == "ALT-102")
            .first()
        )

        print("\nGolden alert:")
        if alert:
            print(f"  Alert ID:     {alert.alert_id}")
            print(f"  Customer:     {alert.customer_id}")
            print(f"  Transaction:  {alert.transaction_id}")
            print(f"  Type:         {alert.alert_type}")
            print(f"  Severity:     {alert.severity}")
            print(f"  Status:       {alert.status}")
        else:
            print("  ERROR: ALT-102 not found")

        # -------------------------------------------------
        # Golden transactions
        # -------------------------------------------------

        golden_ids = [
            "TXN1042",
            "TXN1043",
            "TXN1047",
        ]

        transactions = (
            db.query(Transaction)
            .filter(Transaction.transaction_id.in_(golden_ids))
            .order_by(Transaction.timestamp)
            .all()
        )

        print("\nGolden transactions:")

        for transaction in transactions:
            print(
                f"  {transaction.transaction_id} | "
                f"{transaction.timestamp} | "
                f"{transaction.transaction_type} | "
                f"{transaction.amount:.2f} "
                f"{transaction.currency} | "
                f"{transaction.country}"
            )

        # -------------------------------------------------
        # Sanctions entities
        # -------------------------------------------------

        sanctions = db.query(SanctionsEntity).all()

        print("\nSanctions/watchlist entities:")

        for entity in sanctions:
            print(
                f"  {entity.entity_id} | "
                f"{entity.name} | "
                f"{entity.country} | "
                f"{entity.match_type} | "
                f"{entity.risk_level}"
            )

        print("\n" + "=" * 60)
        print("VERIFICATION COMPLETE")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    main()

