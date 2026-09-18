import json
import logging
from datetime import datetime, timezone
from typing import Any


logger = logging.getLogger("aml_investigator.audit")


SENSITIVE_KEYS = {
    "name",
    "customer_name",
    "account_id",
    "address",
    "phone",
    "email",
    "ssn",
    "pan",
    "passport",
    "raw_customer_data",
}


def _sanitize(value: Any) -> Any:
    """
    Remove sensitive fields from audit metadata before logging.
    """
    if isinstance(value, dict):
        return {
            key: _sanitize(item)
            for key, item in value.items()
            if key.lower() not in SENSITIVE_KEYS
        }

    if isinstance(value, list):
        return [_sanitize(item) for item in value]

    return value


def build_audit_event(
    *,
    investigation_id: str,
    user_id: str,
    role: str,
    query: str,
    authorization_decision: str,
    outcome: str,
    evidence_references: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a structured audit event.

    This function does not write to a database yet. It provides a
    consistent, sanitized audit representation for the workflow.
    """
    event = {
        "event_type": "investigation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "investigation_id": investigation_id,
        "user_id": user_id,
        "role": role,
        "query": query,
        "authorization_decision": authorization_decision,
        "outcome": outcome,
        "evidence_references": evidence_references or [],
        "metadata": metadata or {},
    }

    return _sanitize(event)


def log_audit_event(event: dict[str, Any]) -> None:
    """
    Write a structured audit event through Python logging.

    Audit records intentionally contain only sanitized metadata.
    """
    logger.info(
        "AUDIT_EVENT %s",
        json.dumps(
            event,
            sort_keys=True,
            default=str,
        ),
    )
