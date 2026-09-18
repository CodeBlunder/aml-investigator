import logging

from app.audit.logger import (
    build_audit_event,
    log_audit_event,
)


def test_build_audit_event_contains_required_fields():
    event = build_audit_event(
        investigation_id="INV-TEST-001",
        user_id="U001",
        role="AML_ANALYST",
        query="Why was TXN1042 flagged?",
        authorization_decision="ALLOW",
        outcome="COMPLETED",
    )

    assert event["event_type"] == "investigation"
    assert event["investigation_id"] == "INV-TEST-001"
    assert event["user_id"] == "U001"
    assert event["role"] == "AML_ANALYST"
    assert event["authorization_decision"] == "ALLOW"
    assert event["outcome"] == "COMPLETED"
    assert "timestamp" in event


def test_audit_event_excludes_sensitive_customer_fields():
    event = build_audit_event(
        investigation_id="INV-TEST-002",
        user_id="U001",
        role="AML_ANALYST",
        query="Investigate TXN1042",
        authorization_decision="ALLOW",
        outcome="COMPLETED",
        metadata={
            "name": "John Smith",
            "customer_name": "John Smith",
            "safe_field": "retained",
        },
    )

    assert "name" not in event["metadata"]
    assert "customer_name" not in event["metadata"]
    assert event["metadata"]["safe_field"] == "retained"


def test_log_audit_event_writes_structured_log(caplog):
    event = build_audit_event(
        investigation_id="INV-TEST-003",
        user_id="U001",
        role="AML_ANALYST",
        query="Investigate TXN1042",
        authorization_decision="ALLOW",
        outcome="COMPLETED",
    )

    with caplog.at_level(
        logging.INFO,
        logger="aml_investigator.audit",
    ):
        log_audit_event(event)

    assert "AUDIT_EVENT" in caplog.text
    assert "INV-TEST-003" in caplog.text
