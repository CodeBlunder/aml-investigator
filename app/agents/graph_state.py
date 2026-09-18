from typing import Any, TypedDict


class InvestigationState(TypedDict, total=False):
    """
    Shared state passed between LangGraph investigation nodes.
    """

    # Request context
    user: Any
    query: str

    # Authorization
    authorized: bool
    authorization_error: str | None

    # Agent outputs
    screening_result: dict[str, Any] | None
    investigation_result: dict[str, Any] | None

    # Structured handoff
    investigation_package: Any

    # Workflow status
    handoff_valid: bool
    evidence_sufficient: bool

    # Audit
    audit_event: dict[str, Any] | None

    # Final response
    final_result: dict[str, Any] | None

    # Errors
    errors: list[str]
