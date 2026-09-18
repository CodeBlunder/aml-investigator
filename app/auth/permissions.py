from enum import Enum


class Role(str, Enum):
    CCO = "CCO"
    AML_ANALYST = "AML_ANALYST"
    EXTERNAL_AUDITOR = "EXTERNAL_AUDITOR"
    RELATIONSHIP_MANAGER = "RELATIONSHIP_MANAGER"


PERMISSIONS = {
    Role.CCO: {
        "transactions",
        "customer_pii",
        "sanctions",
        "alerts",
        "audit",
        "sar",
        "feedback",
    },
    Role.AML_ANALYST: {
        "transactions",
        "customer_masked",
        "sanctions",
        "alerts",
    },
    Role.EXTERNAL_AUDITOR: {
        "audit",
        "decisions",
        "rationale",
        "evidence",
    },
    Role.RELATIONSHIP_MANAGER: {
        "transactions",
        "customer_masked",
        "alerts",
        "assigned_portfolio",
    },
}


def has_permission(role: Role, permission: str) -> bool:
    """Return whether a role has the requested permission."""
    return permission in PERMISSIONS.get(role, set())
