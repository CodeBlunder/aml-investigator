
import re

from langgraph.graph import END, START, StateGraph

from app.agents.graph_state import InvestigationState
from app.agents.investigation_agent import investigate
from app.agents.screening_agent import ScreeningAgent
from app.audit.logger import build_audit_event, log_audit_event
from app.auth.context import UserContext
from app.auth.permissions import has_permission
from app.db import SessionLocal
from app.tools.investigation_tools import (
    get_customer,
    get_transaction,
)


def authorization_node(
    state: InvestigationState,
) -> InvestigationState:
    """
    Initial authorization gate.

    The prototype expects an authenticated UserContext.

    Transaction-specific requests require transaction access.
    Customer-specific requests require customer access.
    """

    user = state.get("user")
    query = state.get("query", "")

    # ---------------------------------------------------------
    # USER AUTHENTICATION
    # ---------------------------------------------------------

    if not isinstance(user, UserContext):
        return {
            **state,
            "authorized": False,
            "authorization_error": (
                "Authenticated UserContext is required."
            ),
            "error_type": "ACCESS_DENIED",
            "investigation_result": None,
            "screening_result": {
                "success": False,
                "error": "ACCESS_DENIED",
                "error_type": "ACCESS_DENIED",
                "message": (
                    "Authenticated UserContext is required."
                ),
            },
            "errors": [
                *state.get("errors", []),
                "Authorization failed: UserContext is required.",
            ],
        }

    query_upper = query.upper()

    # ---------------------------------------------------------
    # TRANSACTION ACCESS CHECK
    # ---------------------------------------------------------

    transaction_requested = bool(
        re.search(
            r"\bTXN(?:-[A-Z0-9]+|\d+)\b",
            query_upper,
        )
    )

    if transaction_requested and not has_permission(
        user.role,
        "transactions",
    ):
        return {
            **state,
            "authorized": False,
            "authorization_error": (
                "The current role is not authorized "
                "to access transactions."
            ),
            "error_type": "ACCESS_DENIED",
            "investigation_result": None,
            "screening_result": {
                "success": False,
                "error": "ACCESS_DENIED",
                "error_type": "ACCESS_DENIED",
                "message": (
                    "The current role is not authorized "
                    "to access transactions."
                ),
            },
            "errors": [
                *state.get("errors", []),
                "Authorization failed: transaction access denied.",
            ],
        }

    # ---------------------------------------------------------
    # CUSTOMER ACCESS CHECK
    # ---------------------------------------------------------

    customer_requested = bool(
        re.search(
            r"\bC\d+\b",
            query_upper,
        )
    )

    if customer_requested:
        has_customer_access = (
            has_permission(user.role, "customer_pii")
            or has_permission(user.role, "customer_masked")
        )

        if not has_customer_access:
            return {
                **state,
                "authorized": False,
                "authorization_error": (
                    "The current role is not authorized "
                    "to access customer data."
                ),
                "error_type": "ACCESS_DENIED",
                "investigation_result": None,
                "screening_result": {
                    "success": False,
                    "error": "ACCESS_DENIED",
                    "error_type": "ACCESS_DENIED",
                    "message": (
                        "The current role is not authorized "
                        "to access customer data."
                    ),
                },
                "errors": [
                    *state.get("errors", []),
                    "Authorization failed: customer access denied.",
                ],
            }

    return {
        **state,
        "authorized": True,
        "authorization_error": None,
        "error_type": None,
    }


def authorization_router(
    state: InvestigationState,
) -> str:
    """
    Decide whether the workflow can proceed past authorization.
    """

    if state.get("authorized") is True:
        return "screening"

    return "audit"


def screening_node(
    state: InvestigationState,
) -> InvestigationState:
    """
    Run the Screening Agent and create the structured handoff.

    Query understanding is deterministic in this prototype.
    """

    user = state["user"]
    query = state.get("query", "")

    db = SessionLocal()

    try:
        agent = ScreeningAgent(db)

        transaction_id = None
        alert_id = None
        customer_id = None
        sanctions_query = None

        query_upper = query.upper()

        # -----------------------------------------------------
        # TRANSACTION ID
        # -----------------------------------------------------

        transaction_match = re.search(
            r"\bTXN(?:-[A-Z0-9]+|\d+)\b",
            query_upper,
        )

        if transaction_match:
            transaction_id = transaction_match.group(0)

        # -----------------------------------------------------
        # ALERT ID
        # -----------------------------------------------------

        alert_match = re.search(
            r"\bALT-\d+\b",
            query_upper,
        )

        if alert_match:
            alert_id = alert_match.group(0)

        # -----------------------------------------------------
        # CUSTOMER ID
        # -----------------------------------------------------

        customer_match = re.search(
            r"\bC\d+\b",
            query_upper,
        )

        if customer_match:
            customer_id = customer_match.group(0)

        # -----------------------------------------------------
        # PRIMARY TRANSACTION VALIDATION
        # -----------------------------------------------------

        if transaction_id:
            transaction_result = get_transaction(
                db,
                user,
                transaction_id,
            )

            if not transaction_result.get("success"):
                error_type = transaction_result.get(
                    "error",
                    "TRANSACTION_ACCESS_FAILED",
                )

                message = transaction_result.get(
                    "message",
                    "Unable to retrieve transaction.",
                )

                return {
                    **state,
                    "error_type": error_type,
                    "screening_result": {
                        "success": False,
                        "error": error_type,
                        "error_type": error_type,
                        "message": message,
                    },
                    "investigation_package": None,
                    "errors": [
                        *state.get("errors", []),
                        (
                            "Screening Agent transaction retrieval "
                            "failed: "
                            + error_type
                        ),
                    ],
                }

        # -----------------------------------------------------
        # SANCTIONS QUERY UNDERSTANDING
        # -----------------------------------------------------

        sanctions_requested = any(
            keyword in query_upper
            for keyword in (
                "SANCTION",
                "WATCHLIST",
            )
        )

        if sanctions_requested and customer_id:
            customer_result = get_customer(
                db,
                user,
                customer_id,
            )

            if not customer_result.get("success"):
                error_type = customer_result.get(
                    "error",
                    "CUSTOMER_ACCESS_FAILED",
                )

                message = customer_result.get(
                    "message",
                    "Unable to retrieve customer.",
                )

                return {
                    **state,
                    "error_type": error_type,
                    "screening_result": {
                        "success": False,
                        "error": error_type,
                        "error_type": error_type,
                        "message": message,
                    },
                    "investigation_package": None,
                    "errors": [
                        *state.get("errors", []),
                        (
                            "Screening Agent customer retrieval "
                            "failed: "
                            + error_type
                        ),
                    ],
                }

            customer_data = customer_result.get("data")

            if isinstance(customer_data, dict):
                sanctions_query = customer_data.get("name")

        # -----------------------------------------------------
        # RUN SCREENING AGENT
        # -----------------------------------------------------

        package = agent.investigate(
            user=user,
            customer_id=customer_id,
            transaction_id=transaction_id,
            alert_id=alert_id,
            sanctions_query=sanctions_query,
            user_query=query,
        )

        result = {
            "success": True,
            "agent": "Screening Agent",
            "investigation_package": package,
        }

        return {
            **state,
            "error_type": None,
            "screening_result": result,
            "investigation_package": package,
        }

    except Exception as exc:
        return {
            **state,
            "error_type": "SCREENING_AGENT_FAILED",
            "screening_result": {
                "success": False,
                "error": "SCREENING_AGENT_FAILED",
                "error_type": "SCREENING_AGENT_FAILED",
                "message": str(exc),
            },
            "investigation_package": None,
            "errors": [
                *state.get("errors", []),
                f"Screening Agent failed: {exc}",
            ],
        }

    finally:
        db.close()


def handoff_validation_node(
    state: InvestigationState,
) -> InvestigationState:
    """
    Validate that Screening Agent produced a usable handoff.
    """

    package = state.get("investigation_package")
    screening_result = state.get("screening_result")

    if (
        isinstance(screening_result, dict)
        and screening_result.get("success") is False
    ):
        return {
            **state,
            "handoff_valid": False,
            "errors": [
                *state.get("errors", []),
                "Screening Agent failed to produce a valid handoff.",
            ],
        }

    if package is None:
        return {
            **state,
            "handoff_valid": False,
            "errors": [
                *state.get("errors", []),
                (
                    "Screening Agent did not produce "
                    "an InvestigationPackage."
                ),
            ],
        }

    return {
        **state,
        "handoff_valid": True,
    }


def handoff_router(
    state: InvestigationState,
) -> str:
    """
    Continue only when the Screening Agent handoff is valid.
    """

    if state.get("handoff_valid") is True:
        return "investigation"

    return "audit"


def investigation_node(
    state: InvestigationState,
) -> InvestigationState:
    """
    Run the Investigation Agent using the Screening Agent handoff.
    """

    user = state["user"]
    package = state["investigation_package"]

    result = investigate(
        user,
        package,
    )

    if result.get("success") is not True:
        error_type = result.get(
            "error_type"
        ) or result.get(
            "error",
            "INVESTIGATION_AGENT_FAILED",
        )

        return {
            **state,
            "error_type": error_type,
            "investigation_result": result,
            "errors": [
                *state.get("errors", []),
                error_type,
            ],
        }

    return {
        **state,
        "error_type": None,
        "investigation_result": result,
        "evidence_sufficient": result.get(
            "evidence_sufficiency",
            {},
        ).get(
            "sufficient",
            False,
        ),
    }


def _build_final_result(
    state: InvestigationState,
) -> dict:
    """
    Build one consistent result for the caller.

    All terminal paths pass through this function so that:
    - successful investigations return success=True
    - authorization failures return ACCESS_DENIED
    - missing transactions return NOT_FOUND
    - other failures preserve their machine-readable error type
    """

    screening_result = state.get("screening_result")
    investigation_result = state.get("investigation_result")

    if not isinstance(screening_result, dict):
        screening_result = {}

    if not isinstance(investigation_result, dict):
        investigation_result = {}

    # ---------------------------------------------------------
    # DETERMINE ERROR TYPE
    # ---------------------------------------------------------

    error_type = (
        state.get("error_type")
        or screening_result.get("error_type")
        or screening_result.get("error")
        or investigation_result.get("error_type")
        or investigation_result.get("error")
    )

    # Authorization failures always remain explicit.
    if state.get("authorized") is False:
        error_type = error_type or "ACCESS_DENIED"

    # ---------------------------------------------------------
    # FAILED WORKFLOW
    # ---------------------------------------------------------

    if error_type:
        message = (
            state.get("authorization_error")
            or screening_result.get("message")
            or investigation_result.get("message")
            or "Investigation could not be completed."
        )

        return {
            "success": False,
            "error_type": error_type,
            "error": error_type,
            "message": message,
            "authorized": state.get(
                "authorized",
                False,
            ),
            "audit_event": state.get("audit_event"),
        }

    # ---------------------------------------------------------
    # SUCCESSFUL WORKFLOW
    # ---------------------------------------------------------

    return {
        "success": True,
        "agent": "Investigation Graph",
        "investigation_id": (
            investigation_result.get("investigation_id")
            or getattr(
                state.get("investigation_package"),
                "investigation_id",
                None,
            )
        ),
        "screening_result": screening_result,
        "investigation_result": investigation_result,
        "investigation_package": state.get(
            "investigation_package"
        ),
        "evidence_sufficient": state.get(
            "evidence_sufficient",
            False,
        ),
        "audit_event": state.get("audit_event"),
    }


def audit_logging_node(
    state: InvestigationState,
) -> InvestigationState:
    """
    Create and write a sanitized audit event.

    Both successful and failed workflows are audited.

    The final_result is also created here because every graph
    termination path passes through audit logging.
    """

    user = state.get("user")
    query = state.get("query", "")

    package = state.get("investigation_package")
    investigation_result = state.get("investigation_result")
    screening_result = state.get("screening_result")

    # ---------------------------------------------------------
    # USER UNAVAILABLE
    # ---------------------------------------------------------

    if not isinstance(user, UserContext):
        final_result = {
            "success": False,
            "error_type": "ACCESS_DENIED",
            "error": "ACCESS_DENIED",
            "message": (
                "Authenticated UserContext is required."
            ),
            "authorized": False,
        }

        return {
            **state,
            "error_type": "ACCESS_DENIED",
            "final_result": final_result,
            "errors": [
                *state.get("errors", []),
                (
                    "Audit logging skipped: "
                    "UserContext is unavailable."
                ),
            ],
        }

    # ---------------------------------------------------------
    # INVESTIGATION ID
    # ---------------------------------------------------------

    investigation_id = "UNKNOWN"

    if package is not None:
        investigation_id = getattr(
            package,
            "investigation_id",
            "UNKNOWN",
        )

    # ---------------------------------------------------------
    # EVIDENCE REFERENCES
    # ---------------------------------------------------------

    evidence_references = []

    if isinstance(investigation_result, dict):
        for item in investigation_result.get(
            "regulatory_evidence",
            [],
        ):
            if isinstance(item, dict):
                requirement_id = item.get(
                    "requirement_id"
                )

                if requirement_id:
                    evidence_references.append(
                        str(requirement_id)
                    )

    # ---------------------------------------------------------
    # AUTHORIZATION DECISION
    # ---------------------------------------------------------

    if state.get("authorized") is True:
        authorization_decision = "ALLOW"
    else:
        authorization_decision = "DENY"

    # ---------------------------------------------------------
    # OUTCOME
    # ---------------------------------------------------------

    if (
        isinstance(screening_result, dict)
        and screening_result.get("success") is False
    ):
        outcome = "FAILED"

    elif investigation_result is None:
        outcome = "NOT_COMPLETED"

    elif investigation_result.get("success") is True:
        outcome = "COMPLETED"

    else:
        outcome = "FAILED"

    # ---------------------------------------------------------
    # AUDIT EVENT
    # ---------------------------------------------------------

    event = build_audit_event(
        investigation_id=investigation_id,
        user_id=user.user_id,
        role=user.role.value,
        query=query,
        authorization_decision=authorization_decision,
        outcome=outcome,
        evidence_references=list(
            dict.fromkeys(evidence_references)
        ),
        metadata={
            "evidence_sufficient": state.get(
                "evidence_sufficient",
                False,
            ),
            "error_count": len(
                state.get("errors", [])
            ),
            "error_type": state.get(
                "error_type"
            ),
            "authorization_error": state.get(
                "authorization_error"
            ),
            "screening_error": (
                screening_result.get("error")
                if isinstance(screening_result, dict)
                else None
            ),
            "screening_error_type": (
                screening_result.get("error_type")
                if isinstance(screening_result, dict)
                else None
            ),
        },
    )

    log_audit_event(event)

    # ---------------------------------------------------------
    # BUILD FINAL RESULT
    # ---------------------------------------------------------

    updated_state = {
        **state,
        "audit_event": event,
    }

    final_result = _build_final_result(
        updated_state
    )

    return {
        **updated_state,
        "final_result": final_result,
    }


def build_investigation_graph():
    """
    Build the AML investigation LangGraph workflow.

    Normal flow:

        START
          -> Authorization
          -> Screening Agent
          -> Handoff Validation
          -> Investigation Agent
          -> Audit Logging
          -> END

    Failed authorization and failed handoff paths are also
    sent to Audit Logging before termination.
    """

    graph = StateGraph(InvestigationState)

    graph.add_node(
        "authorization",
        authorization_node,
    )

    graph.add_node(
        "screening",
        screening_node,
    )

    graph.add_node(
        "handoff_validation",
        handoff_validation_node,
    )

    graph.add_node(
        "investigation",
        investigation_node,
    )

    graph.add_node(
        "audit_logging",
        audit_logging_node,
    )

    # ---------------------------------------------------------
    # START -> AUTHORIZATION
    # ---------------------------------------------------------

    graph.add_edge(
        START,
        "authorization",
    )

    # ---------------------------------------------------------
    # AUTHORIZATION ROUTING
    # ---------------------------------------------------------

    graph.add_conditional_edges(
        "authorization",
        authorization_router,
        {
            "screening": "screening",
            "audit": "audit_logging",
        },
    )

    # ---------------------------------------------------------
    # SCREENING -> HANDOFF VALIDATION
    # ---------------------------------------------------------

    graph.add_edge(
        "screening",
        "handoff_validation",
    )

    # ---------------------------------------------------------
    # HANDOFF ROUTING
    # ---------------------------------------------------------

    graph.add_conditional_edges(
        "handoff_validation",
        handoff_router,
        {
            "investigation": "investigation",
            "audit": "audit_logging",
        },
    )

    # ---------------------------------------------------------
    # INVESTIGATION -> AUDIT
    # ---------------------------------------------------------

    graph.add_edge(
        "investigation",
        "audit_logging",
    )

    # ---------------------------------------------------------
    # AUDIT -> END
    # ---------------------------------------------------------

    graph.add_edge(
        "audit_logging",
        END,
    )

    return graph.compile()


investigation_graph = build_investigation_graph()
