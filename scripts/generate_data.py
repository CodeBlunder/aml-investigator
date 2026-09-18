
from pathlib import Path
from datetime import datetime, timedelta
import random
import pandas as pd


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

SEED = 42
random.seed(SEED)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"

CUSTOMER_DIR = DATA_DIR / "customers"
TRANSACTION_DIR = DATA_DIR / "transactions"
ALERT_DIR = DATA_DIR / "alerts"
SANCTIONS_DIR = DATA_DIR / "sanctions"

for directory in [
    CUSTOMER_DIR,
    TRANSACTION_DIR,
    ALERT_DIR,
    SANCTIONS_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Customers
# ---------------------------------------------------------

def generate_customers(count=75):
    customers = []

    occupations = [
        "Software Engineer",
        "Accountant",
        "Consultant",
        "Business Owner",
        "Trader",
        "Doctor",
        "Teacher",
        "Import Export Business",
        "Real Estate",
        "Financial Services",
    ]

    countries = [
        "India",
        "Singapore",
        "United Kingdom",
        "United States",
        "United Arab Emirates",
        "Germany",
        "Japan",
        "Malaysia",
    ]

    for i in range(1, count + 1):
        customer_id = f"C{i:03d}"

        customers.append(
            {
                "customer_id": customer_id,
                "name": f"Customer {i:03d}",
                "account_id": f"ACC{i:04d}",
                "country": random.choice(countries),
                "occupation": random.choice(occupations),
                "business_type": (
                    "Individual"
                    if i % 3 != 0
                    else "Corporate"
                ),
                "risk_rating": random.choice(
                    ["LOW", "MEDIUM", "HIGH"]
                ),
                "portfolio_id": f"PORT-{((i - 1) % 5) + 1:03d}",
                "kyc_status": random.choice(
                    ["VERIFIED", "VERIFIED", "VERIFIED", "REVIEW"]
                ),
            }
        )

    # Golden investigation customer
    customers.append(
        {
            "customer_id": "C102",
            "name": "Arjun Mehta",
            "account_id": "ACC0102",
            "country": "India",
            "occupation": "Import Export Business",
            "business_type": "Corporate",
            "risk_rating": "HIGH",
            "portfolio_id": "PORT-002",
            "kyc_status": "VERIFIED",
        }
    )

    return customers


# ---------------------------------------------------------
# Transactions
# ---------------------------------------------------------

def generate_transactions(customers):
    transactions = []

    start_date = datetime(2025, 1, 1)

    transaction_types = [
        "CREDIT",
        "DEBIT",
        "TRANSFER",
    ]

    countries = [
        "India",
        "Singapore",
        "United Kingdom",
        "United States",
        "United Arab Emirates",
        "Germany",
        "Japan",
        "Malaysia",
    ]

    transaction_id = 2000

    # Ordinary transactions
    for i in range(380):
        customer = random.choice(customers)

        amount = round(random.uniform(500, 25000), 2)

        transaction_id += 1

        transactions.append(
            {
                "transaction_id": f"TXN{transaction_id}",
                "customer_id": customer["customer_id"],
                "account_id": customer["account_id"],
                "timestamp": (
                    start_date
                    + timedelta(
                        days=random.randint(0, 180),
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59),
                    )
                ).isoformat(),
                "transaction_type": random.choice(transaction_types),
                "amount": amount,
                "currency": "USD",
                "counterparty": f"CP-{random.randint(100, 999)}",
                "country": random.choice(countries),
                "description": "Routine account transaction",
            }
        )

    # -----------------------------------------------------
    # Golden investigation scenario
    # -----------------------------------------------------

    golden_transactions = [
        {
            "transaction_id": "TXN1042",
            "customer_id": "C102",
            "account_id": "ACC0102",
            "timestamp": "2025-06-15T09:10:00",
            "transaction_type": "CREDIT",
            "amount": 9800.00,
            "currency": "USD",
            "counterparty": "CP-OFFSHORE-01",
            "country": "United Arab Emirates",
            "description": "Incoming international transfer",
        },
        {
            "transaction_id": "TXN1043",
            "customer_id": "C102",
            "account_id": "ACC0102",
            "timestamp": "2025-06-15T10:05:00",
            "transaction_type": "CREDIT",
            "amount": 9700.00,
            "currency": "USD",
            "counterparty": "CP-OFFSHORE-02",
            "country": "United Arab Emirates",
            "description": "Incoming international transfer",
        },
        {
            "transaction_id": "TXN1047",
            "customer_id": "C102",
            "account_id": "ACC0102",
            "timestamp": "2025-06-15T11:20:00",
            "transaction_type": "DEBIT",
            "amount": 18500.00,
            "currency": "USD",
            "counterparty": "CP-INTL-77",
            "country": "Singapore",
            "description": "Rapid outgoing international transfer",
        },
    ]

    transactions.extend(golden_transactions)

    return transactions


# ---------------------------------------------------------
# Alerts
# ---------------------------------------------------------

def generate_alerts(transactions):
    alerts = []

    # Golden alert
    alerts.append(
        {
            "alert_id": "ALT-102",
            "customer_id": "C102",
            "transaction_id": "TXN1042",
            "alert_type": "SUSPICIOUS_TRANSACTION_PATTERN",
            "severity": "HIGH",
            "status": "OPEN",
            "created_at": "2025-06-15T12:00:00",
            "description": (
                "Multiple incoming international transactions "
                "followed by rapid outgoing movement."
            ),
        }
    )

    # Additional alerts
    alert_counter = 1

    for transaction in transactions[:20]:
        if transaction["customer_id"] == "C102":
            continue

        alert_counter += 1

        alerts.append(
            {
                "alert_id": f"ALT-{alert_counter:03d}",
                "customer_id": transaction["customer_id"],
                "transaction_id": transaction["transaction_id"],
                "alert_type": random.choice(
                    [
                        "HIGH_VALUE",
                        "UNUSUAL_GEOGRAPHY",
                        "RAPID_MOVEMENT",
                        "REPEATED_TRANSFERS",
                    ]
                ),
                "severity": random.choice(
                    ["LOW", "MEDIUM", "HIGH"]
                ),
                "status": random.choice(
                    ["OPEN", "CLOSED"]
                ),
                "created_at": transaction["timestamp"],
                "description": "Automated transaction monitoring alert.",
            }
        )

    return alerts


# ---------------------------------------------------------
# Sanctions / Watchlist
# ---------------------------------------------------------

def generate_sanctions():
    return [
        {
            "entity_id": "SAN-001",
            "name": "Arjun Mehta Trading LLC",
            "aliases": "A. Mehta Trading;Arjun M Trading",
            "country": "United Arab Emirates",
            "list_name": "Synthetic Watchlist",
            "match_type": "PROBABLE",
            "risk_level": "HIGH",
        },
        {
            "entity_id": "SAN-002",
            "name": "Global Meridian Holdings",
            "aliases": "Global Meridian;GM Holdings",
            "country": "Singapore",
            "list_name": "Synthetic Watchlist",
            "match_type": "EXACT",
            "risk_level": "HIGH",
        },
        {
            "entity_id": "SAN-003",
            "name": "Eastern Pacific Trading",
            "aliases": "EPT;Eastern Pacific",
            "country": "Malaysia",
            "list_name": "Synthetic Watchlist",
            "match_type": "PROBABLE",
            "risk_level": "MEDIUM",
        },
        {
            "entity_id": "SAN-004",
            "name": "John Peterson",
            "aliases": "J. Peterson",
            "country": "United Kingdom",
            "list_name": "Synthetic Watchlist",
            "match_type": "EXACT",
            "risk_level": "HIGH",
        },
    ]


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():
    print("Generating AML Investigator synthetic dataset...")

    customers = generate_customers()
    transactions = generate_transactions(customers)
    alerts = generate_alerts(transactions)
    sanctions = generate_sanctions()

    pd.DataFrame(customers).to_csv(
        CUSTOMER_DIR / "customers.csv",
        index=False,
    )

    pd.DataFrame(transactions).to_csv(
        TRANSACTION_DIR / "transactions.csv",
        index=False,
    )

    pd.DataFrame(alerts).to_csv(
        ALERT_DIR / "alerts.csv",
        index=False,
    )

    pd.DataFrame(sanctions).to_csv(
        SANCTIONS_DIR / "sanctions.csv",
        index=False,
    )

    print()
    print("Dataset generation complete.")
    print(f"Customers:    {len(customers)}")
    print(f"Transactions: {len(transactions)}")
    print(f"Alerts:       {len(alerts)}")
    print(f"Sanctions:    {len(sanctions)}")
    print()
    print("Golden investigation case:")
    print("  Customer:    C102")
    print("  Alert:       ALT-102")
    print("  Transactions: TXN1042, TXN1043, TXN1047")


if __name__ == "__main__":
    main()

