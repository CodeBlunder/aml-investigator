from app.scoring.risk_engine import (
    calculate_risk,
    detect_high_value_transactions,
    detect_multiple_transactions,
    detect_rapid_movement,
    detect_structuring,
    detect_unusual_geography,
)


def make_transaction(
    transaction_id,
    timestamp,
    transaction_type,
    amount,
    country,
    currency="USD",
):
    return {
        "transaction_id": transaction_id,
        "customer_id": "C102",
        "account_id": "ACC0102",
        "timestamp": timestamp,
        "transaction_type": transaction_type,
        "amount": amount,
        "currency": currency,
        "counterparty": "TEST",
        "country": country,
        "description": "Test transaction",
    }


def test_high_value_transaction_is_detected():
    transactions = [
        make_transaction(
            "TXN9001",
            "2025-06-15T09:00:00",
            "DEBIT",
            15000,
            "Singapore",
        )
    ]

    signals = detect_high_value_transactions(
        transactions
    )

    assert len(signals) == 1
    assert signals[0]["signal"] == "HIGH_VALUE_TRANSACTION"
    assert signals[0]["weight"] == 20
    assert signals[0]["transaction_ids"] == ["TXN9001"]


def test_transaction_below_high_value_threshold_is_not_flagged():
    transactions = [
        make_transaction(
            "TXN9002",
            "2025-06-15T09:00:00",
            "DEBIT",
            5000,
            "Singapore",
        )
    ]

    signals = detect_high_value_transactions(
        transactions
    )

    assert signals == []


def test_possible_structuring_is_detected():
    transactions = [
        make_transaction(
            "TXN9003",
            "2025-06-15T09:00:00",
            "CREDIT",
            9800,
            "United Arab Emirates",
        ),
        make_transaction(
            "TXN9004",
            "2025-06-15T10:00:00",
            "CREDIT",
            9700,
            "United Arab Emirates",
        ),
    ]

    signals = detect_structuring(transactions)

    assert len(signals) == 1
    assert signals[0]["signal"] == "POSSIBLE_STRUCTURING"
    assert signals[0]["weight"] == 25

    assert set(signals[0]["transaction_ids"]) == {
        "TXN9003",
        "TXN9004",
    }


def test_single_near_threshold_transaction_is_not_structuring():
    transactions = [
        make_transaction(
            "TXN9005",
            "2025-06-15T09:00:00",
            "CREDIT",
            9800,
            "United Arab Emirates",
        )
    ]

    signals = detect_structuring(transactions)

    assert signals == []


def test_rapid_movement_is_detected():
    transactions = [
        make_transaction(
            "TXN9006",
            "2025-06-15T09:00:00",
            "CREDIT",
            9800,
            "United Arab Emirates",
        ),
        make_transaction(
            "TXN9007",
            "2025-06-15T10:05:00",
            "DEBIT",
            9500,
            "Singapore",
        ),
    ]

    signals = detect_rapid_movement(transactions)

    assert len(signals) == 1
    assert signals[0]["signal"] == "RAPID_MOVEMENT"
    assert signals[0]["weight"] == 25
    assert signals[0]["transaction_ids"] == [
        "TXN9006",
        "TXN9007",
    ]


def test_rapid_movement_outside_window_is_not_detected():
    transactions = [
        make_transaction(
            "TXN9008",
            "2025-06-15T09:00:00",
            "CREDIT",
            9800,
            "United Arab Emirates",
        ),
        make_transaction(
            "TXN9009",
            "2025-06-15T14:00:00",
            "DEBIT",
            9500,
            "Singapore",
        ),
    ]

    signals = detect_rapid_movement(transactions)

    assert signals == []


def test_unusual_geography_is_detected():
    transactions = [
        make_transaction(
            "TXN9010",
            "2025-06-15T09:00:00",
            "CREDIT",
            5000,
            "United Arab Emirates",
        )
    ]

    signals = detect_unusual_geography(transactions)

    assert len(signals) == 1
    assert signals[0]["signal"] == "UNUSUAL_GEOGRAPHY"
    assert signals[0]["weight"] == 15


def test_normal_geography_is_not_flagged():
    transactions = [
        make_transaction(
            "TXN9011",
            "2025-06-15T09:00:00",
            "CREDIT",
            5000,
            "Canada",
        )
    ]

    signals = detect_unusual_geography(transactions)

    assert signals == []


def test_multiple_transactions_signal():
    transactions = [
        make_transaction(
            "TXN9012",
            "2025-06-15T09:00:00",
            "CREDIT",
            1000,
            "Canada",
        ),
        make_transaction(
            "TXN9013",
            "2025-06-15T10:00:00",
            "CREDIT",
            2000,
            "Canada",
        ),
        make_transaction(
            "TXN9014",
            "2025-06-15T11:00:00",
            "DEBIT",
            1500,
            "Canada",
        ),
    ]

    signals = detect_multiple_transactions(
        transactions
    )

    assert len(signals) == 1
    assert signals[0]["signal"] == "MULTIPLE_TRANSACTIONS"
    assert signals[0]["weight"] == 10


def test_empty_transaction_set_is_low_risk():
    result = calculate_risk([])

    assert result["score"] == 0
    assert result["risk_level"] == "LOW"
    assert result["signals"] == []
    assert result["transaction_count"] == 0


def test_golden_case_produces_high_risk():
    transactions = [
        make_transaction(
            "TXN1042",
            "2025-06-15T09:10:00",
            "CREDIT",
            9800,
            "United Arab Emirates",
        ),
        make_transaction(
            "TXN1043",
            "2025-06-15T10:05:00",
            "CREDIT",
            9700,
            "United Arab Emirates",
        ),
        make_transaction(
            "TXN1047",
            "2025-06-15T11:20:00",
            "DEBIT",
            18500,
            "Singapore",
        ),
    ]

    result = calculate_risk(transactions)

    assert result["risk_level"] == "HIGH"
    assert result["score"] > 0
    assert result["transaction_count"] == 3

    signal_names = {
        signal["signal"]
        for signal in result["signals"]
    }

    assert "HIGH_VALUE_TRANSACTION" in signal_names
    assert "POSSIBLE_STRUCTURING" in signal_names
    assert "RAPID_MOVEMENT" in signal_names
    assert "UNUSUAL_GEOGRAPHY" in signal_names
    assert "MULTIPLE_TRANSACTIONS" in signal_names