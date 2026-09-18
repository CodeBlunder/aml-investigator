import sys
from pathlib import Path
from typing import Any

import streamlit as st

# Allow imports from the project root when Streamlit runs this file.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from sqlalchemy import text
from app.agents.investigation_graph import build_investigation_graph
from app.auth.context import UserContext
from app.auth.permissions import Role
from app.db import SessionLocal
from app.tools.investigation_tools import find_alerts
from eval.run_evaluation import load_cases, run_case

st.set_page_config(
    page_title="AML Investigator",
    page_icon="🔎",
    layout="wide",
)


# ==================================================================
# HELPERS
# ==================================================================

def create_user_context(
    role_name: str,
    portfolio_id: str | None,
) -> UserContext:
    """Create the authenticated user context used by the graph."""

    role = Role(role_name)

    return UserContext(
        user_id=f"UI-{role_name}",
        role=role,
        portfolio_id=(
            portfolio_id
            if role == Role.RELATIONSHIP_MANAGER
            else None
        ),
    )


def run_investigation(
    user: UserContext,
    query: str,
) -> dict:
    """Run the existing investigation graph."""

    graph = build_investigation_graph()

    state = {
        "user": user,
        "query": query,
        "authorized": False,
        "authorization_error": None,
        "screening_result": None,
        "investigation_result": None,
        "investigation_package": None,
        "handoff_valid": False,
        "evidence_sufficient": False,
        "audit_event": None,
        "final_result": None,
        "errors": [],
        "error_type": None,
    }

    return graph.invoke(state)


def model_to_dict(value: Any) -> dict:
    """
    Convert a Pydantic model or dictionary into a dictionary.
    """

    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if hasattr(value, "model_dump"):
        return value.model_dump()

    if hasattr(value, "dict"):
        return value.dict()

    return {}


def model_list_to_dicts(value: Any) -> list[dict]:
    """Convert a list of Pydantic models/dicts into dictionaries."""

    if not value:
        return []

    return [
        model_to_dict(item)
        for item in value
    ]


# ==================================================================
# INVESTIGATION DISPLAY
# ==================================================================

def display_transactions(package: dict) -> None:
    """Display transaction evidence."""

    transactions = model_list_to_dicts(
        package.get("transactions")
    )

    if not transactions:
        st.info(
            "No transaction evidence returned."
        )
        return

    rows = []

    for transaction in transactions:
        rows.append(
            {
                "Transaction ID": transaction.get(
                    "transaction_id"
                ),
                "Customer": transaction.get(
                    "customer_id"
                ),
                "Account": transaction.get(
                    "account_id"
                ),
                "Timestamp": transaction.get(
                    "timestamp"
                ),
                "Type": transaction.get(
                    "transaction_type"
                ),
                "Amount": transaction.get(
                    "amount"
                ),
                "Currency": transaction.get(
                    "currency"
                ),
                "Country": transaction.get(
                    "country"
                ),
                "Counterparty": transaction.get(
                    "counterparty"
                ),
            }
        )

    st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
    )


def display_risk(package: dict) -> None:
    """Display deterministic risk assessment."""

    risk = model_to_dict(
        package.get("risk_assessment")
    )

    if not risk:
        st.info(
            "No risk assessment returned."
        )
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Risk score",
            risk.get("score", 0),
        )

    with col2:
        st.metric(
            "Risk level",
            risk.get(
                "risk_level",
                "UNKNOWN",
            ),
        )

    with col3:
        st.metric(
            "Transactions",
            risk.get(
                "transaction_count",
                0,
            ),
        )

    signals = model_list_to_dicts(
        risk.get("signals")
    )

    if not signals:
        st.info(
            "No deterministic risk signals detected."
        )
        return

    st.subheader(
        "Risk signals"
    )

    for signal in signals:
        st.markdown(
            f"**{signal.get('signal')}** "
            f"(weight: {signal.get('weight')})"
        )

        st.write(
            signal.get("explanation")
        )

        transaction_ids = (
            signal.get("transaction_ids")
            or []
        )

        if transaction_ids:
            st.caption(
                "Related transactions: "
                + ", ".join(transaction_ids)
            )


def display_alert(package: dict) -> None:
    """Display alert evidence."""

    alert = model_to_dict(
        package.get("alert")
    )

    if not alert:
        st.info(
            "No associated alert found."
        )
        return

    st.subheader(
        "Alert"
    )

    st.json(
        {
            "alert_id": alert.get(
                "alert_id"
            ),
            "customer_id": alert.get(
                "customer_id"
            ),
            "transaction_id": alert.get(
                "transaction_id"
            ),
            "alert_type": alert.get(
                "alert_type"
            ),
            "severity": alert.get(
                "severity"
            ),
            "status": alert.get(
                "status"
            ),
            "created_at": alert.get(
                "created_at"
            ),
            "description": alert.get(
                "description"
            ),
        }
    )


def display_sanctions(package: dict) -> None:
    """Display sanctions/watchlist evidence."""

    sanctions = model_to_dict(
        package.get("sanctions")
    )

    if not sanctions:
        st.info(
            "No sanctions screening result returned."
        )
        return

    matches = model_list_to_dicts(
        sanctions.get("matches")
    )

    if not matches:
        st.success(
            "No sanctions/watchlist matches found."
        )
        return

    st.subheader(
        "Sanctions / watchlist matches"
    )

    for match in matches:
        st.warning(
            f"{match.get('name')} — "
            f"{match.get('match_type')} "
            f"({match.get('risk_level')})"
        )

        st.write(
            f"Matched on: "
            f"{match.get('matched_on')}"
        )

        if match.get("aliases"):
            st.caption(
                f"Aliases: {match.get('aliases')}"
            )


def display_regulatory_evidence(
    investigation: dict,
) -> None:
    """Display regulatory evidence and findings."""

    evidence = model_list_to_dicts(
        investigation.get(
            "regulatory_evidence"
        )
    )

    findings = model_list_to_dicts(
        investigation.get(
            "findings"
        )
    )

    st.subheader(
        "Regulatory evidence"
    )

    if not evidence:
        st.info(
            "No regulatory evidence returned."
        )

    else:
        for item in evidence:
            requirement_id = item.get(
                "requirement_id",
                "Unknown requirement",
            )

            requirement_topic = (
                item.get("requirement_topic")
                or item.get("topic")
                or "Regulatory requirement"
            )

            with st.expander(
                f"{requirement_id} — "
                f"{requirement_topic}"
            ):
                st.write(
                    f"**Requirement:** "
                    f"{item.get('requirement_text')}"
                )

                st.write(
                    f"**Regulation:** "
                    f"{item.get('regulation_id')}"
                )

                st.write(
                    f"**Jurisdiction:** "
                    f"{item.get('jurisdiction')}"
                )

                st.write(
                    f"**Source:** "
                    f"{item.get('source_document')}"
                )

    if findings:
        st.subheader(
            "Investigation findings"
        )

        for finding in findings:
            st.markdown(
                f"**{finding.get('signal')}**"
            )

            st.write(
                finding.get("explanation")
            )

            st.write(
                f"**Finding:** "
                f"{finding.get('finding')}"
            )


# ==================================================================
# AUDIT TRAIL DISPLAY
# ==================================================================

def display_audit_event(
    audit_event: dict | None,
) -> None:
    """
    Display the sanitized audit event generated by the
    investigation graph.
    """

    st.subheader(
        "Audit Event"
    )

    if not audit_event:
        st.info(
            "No audit event is available yet. "
            "Run an investigation first."
        )
        return

    col1, col2 = st.columns(2)

    with col1:
        st.write(
            "**Event type:**",
            audit_event.get(
                "event_type",
                "N/A",
            ),
        )

        st.write(
            "**Investigation ID:**",
            audit_event.get(
                "investigation_id",
                "N/A",
            ),
        )

        st.write(
            "**User ID:**",
            audit_event.get(
                "user_id",
                "N/A",
            ),
        )

        st.write(
            "**Role:**",
            audit_event.get(
                "role",
                "N/A",
            ),
        )

    with col2:
        st.write(
            "**Timestamp:**",
            audit_event.get(
                "timestamp",
                "N/A",
            ),
        )

        st.write(
            "**Authorization:**",
            audit_event.get(
                "authorization_decision",
                "N/A",
            ),
        )

        st.write(
            "**Outcome:**",
            audit_event.get(
                "outcome",
                "N/A",
            ),
        )

    st.write(
        "**Query:**"
    )

    st.code(
        audit_event.get(
            "query",
            "",
        ),
        language="text",
    )

    evidence_references = audit_event.get(
        "evidence_references",
        [],
    )

    st.write(
        "**Evidence references:**"
    )

    if evidence_references:
        for reference in evidence_references:
            st.write(
                f"- {reference}"
            )
    else:
        st.write(
            "None"
        )

    metadata = audit_event.get(
        "metadata",
        {},
    )

    if metadata:
        with st.expander(
            "Audit metadata"
        ):
            st.json(
                metadata
            )


def display_result(result: dict) -> None:
    """Render the final graph result."""

    final_result = (
        result.get("final_result")
        or {}
    )

    # ---------------------------------------------------------
    # FAILED INVESTIGATION
    # ---------------------------------------------------------

    if final_result.get("success") is False:
        error_type = final_result.get(
            "error_type"
        ) or final_result.get(
            "error",
            "UNKNOWN_ERROR",
        )

        message = final_result.get(
            "message",
            "The investigation could not be completed.",
        )

        st.error(
            f"{error_type}: {message}"
        )

        return

    # ---------------------------------------------------------
    # EMPTY RESULT
    # ---------------------------------------------------------

    if not final_result:
        st.error(
            "The investigation returned no final result."
        )

        return

    # ---------------------------------------------------------
    # NORMALIZE INVESTIGATION PACKAGE
    # ---------------------------------------------------------

    package = model_to_dict(
        result.get(
            "investigation_package"
        )
    )

    investigation = model_to_dict(
        result.get(
            "investigation_result"
        )
    )

    # ---------------------------------------------------------
    # EVIDENCE SUFFICIENCY
    # ---------------------------------------------------------

    evidence_sufficient = final_result.get(
        "evidence_sufficient",
        False,
    )

    if evidence_sufficient:
        st.success(
            "Investigation completed with sufficient evidence."
        )
    else:
        st.warning(
            "Evidence is insufficient for a complete conclusion."
        )

    # ---------------------------------------------------------
    # CUSTOMER
    # ---------------------------------------------------------

    customer = model_to_dict(
        package.get("customer")
    )

    if customer:
        st.subheader(
            "Customer"
        )

        customer_columns = st.columns(4)

        with customer_columns[0]:
            st.write(
                f"**Customer ID:** "
                f"{customer.get('customer_id')}"
            )

        with customer_columns[1]:
            st.write(
                f"**Name:** "
                f"{customer.get('name')}"
            )

        with customer_columns[2]:
            st.write(
                f"**Risk:** "
                f"{customer.get('risk_rating')}"
            )

        with customer_columns[3]:
            st.write(
                f"**KYC:** "
                f"{customer.get('kyc_status')}"
            )

    # ---------------------------------------------------------
    # TRANSACTIONS
    # ---------------------------------------------------------

    st.subheader(
        "Transactions"
    )

    display_transactions(
        package
    )

    # ---------------------------------------------------------
    # ALERT + SANCTIONS
    # ---------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:
        display_alert(
            package
        )

    with col2:
        display_sanctions(
            package
        )

    st.divider()

    # ---------------------------------------------------------
    # RISK
    # ---------------------------------------------------------

    st.subheader(
        "Risk assessment"
    )

    display_risk(
        package
    )

    st.divider()

    # ---------------------------------------------------------
    # REGULATORY EVIDENCE
    # ---------------------------------------------------------

    display_regulatory_evidence(
        investigation
    )

    st.divider()

    # ---------------------------------------------------------
    # CONCLUSION
    # ---------------------------------------------------------

    st.subheader(
        "Conclusion"
    )

    conclusion = investigation.get(
        "conclusion",
        "No conclusion was returned.",
    )

    st.info(
        conclusion
    )

    st.caption(
        f"Investigation ID: "
        f"{investigation.get('investigation_id', 'N/A')}"
    )


# ==================================================================
# ALERTS
# ==================================================================

def load_alerts(
    user: UserContext,
    customer_id: str | None = None,
    transaction_id: str | None = None,
) -> list[dict]:
    """
    Load alerts through the existing controlled backend tool.

    The backend requires either customer_id or transaction_id.
    Authorization remains enforced by the backend.
    """

    db = SessionLocal()

    try:
        result = find_alerts(
            db=db,
            user=user,
            customer_id=customer_id,
            transaction_id=transaction_id,
        )

        if not result.get("success"):
            st.error(
                f"{result.get('error', 'ERROR')}: "
                f"{result.get('message', 'Unable to load alerts.')}"
            )

            return []

        return result.get(
            "alerts",
            [],
        )

    finally:
        db.close()


def display_alerts_page(
    user: UserContext,
) -> None:
    """Render the Alerts page."""

    st.header(
        "🚨 Alerts"
    )

    st.caption(
        "Search alerts through the controlled authorization layer."
    )

    # ---------------------------------------------------------
    # SEARCH INPUT
    # ---------------------------------------------------------

    st.subheader(
        "Find alerts"
    )

    search_mode = st.radio(
        "Search by",
        [
            "Customer ID",
            "Transaction ID",
        ],
        horizontal=True,
        key="alert_search_mode",
    )

    search_value = st.text_input(
        search_mode,
        placeholder=(
            "Example: C102"
            if search_mode == "Customer ID"
            else "Example: TXN1042"
        ),
        key="alert_search_input",
    )

    # ---------------------------------------------------------
    # LOAD ALERTS
    # ---------------------------------------------------------

    if st.button(
        "Load Alerts",
        type="primary",
        width="stretch",
        key="load_alerts_button",
    ):
        if not search_value.strip():
            st.warning(
                f"Enter a {search_mode.lower()}."
            )

        else:
            search_value = search_value.strip()

            if search_mode == "Customer ID":
                customer_id = search_value
                transaction_id = None
            else:
                customer_id = None
                transaction_id = search_value

            with st.spinner(
                "Loading alerts..."
            ):
                alerts = load_alerts(
                    user=user,
                    customer_id=customer_id,
                    transaction_id=transaction_id,
                )

                st.session_state[
                    "alerts"
                ] = alerts

                st.session_state[
                    "alert_search_value"
                ] = search_value

                st.session_state[
                    "alert_investigation_active"
                ] = False

                # Clear any previous alert investigation result.
                st.session_state[
                    "alert_investigation_result"
                ] = None

    alerts = st.session_state.get(
        "alerts",
        [],
    )

    # ---------------------------------------------------------
    # DISPLAY ALERT LIST
    # ---------------------------------------------------------

    if not alerts:
        st.info(
            "No alerts loaded. "
            "Enter a customer or transaction ID and click Load Alerts."
        )

        return

    st.subheader(
        f"Alerts ({len(alerts)})"
    )

    rows = []

    for alert in alerts:
        rows.append(
            {
                "Alert ID": alert.get(
                    "alert_id"
                ),
                "Customer": alert.get(
                    "customer_id"
                ),
                "Transaction": alert.get(
                    "transaction_id"
                ),
                "Type": alert.get(
                    "alert_type"
                ),
                "Severity": alert.get(
                    "severity"
                ),
                "Status": alert.get(
                    "status"
                ),
                "Created": alert.get(
                    "created_at"
                ),
            }
        )

    st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
    )

    # ---------------------------------------------------------
    # SELECT ALERT
    # ---------------------------------------------------------

    alert_ids = [
        alert.get("alert_id")
        for alert in alerts
        if alert.get("alert_id")
    ]

    if not alert_ids:
        st.warning(
            "The alert results did not contain alert IDs."
        )

        return

    selected_alert_id = st.selectbox(
        "Select an alert",
        alert_ids,
        key="selected_alert_id",
    )

    selected_alert = next(
        (
            alert
            for alert in alerts
            if alert.get("alert_id")
            == selected_alert_id
        ),
        None,
    )

    if selected_alert:
        st.divider()

        st.subheader(
            f"Alert {selected_alert_id}"
        )

        detail_col1, detail_col2, detail_col3 = st.columns(3)

        with detail_col1:
            st.write(
                f"**Customer:** "
                f"{selected_alert.get('customer_id')}"
            )

        with detail_col2:
            st.write(
                f"**Transaction:** "
                f"{selected_alert.get('transaction_id')}"
            )

        with detail_col3:
            st.write(
                f"**Severity:** "
                f"{selected_alert.get('severity')}"
            )

        st.write(
            f"**Type:** "
            f"{selected_alert.get('alert_type')}"
        )

        st.write(
            f"**Status:** "
            f"{selected_alert.get('status')}"
        )

        if selected_alert.get("description"):
            st.write(
                f"**Description:** "
                f"{selected_alert.get('description')}"
            )

        # -----------------------------------------------------
        # INVESTIGATE SELECTED ALERT
        # -----------------------------------------------------

        if st.button(
            "Investigate Selected Alert",
            type="primary",
            width="stretch",
            key="investigate_selected_alert",
        ):
            alert_id = selected_alert.get(
                "alert_id"
            )

            customer_id = selected_alert.get(
                "customer_id"
            )

            transaction_id = selected_alert.get(
                "transaction_id"
            )

            query = (
                f"Investigate alert {alert_id} for customer "
                f"{customer_id} and transaction {transaction_id}. "
                f"Explain the associated customer information, "
                f"transaction activity, related alerts, deterministic "
                f"risk indicators, sanctions/watchlist evidence, "
                f"and applicable AML requirements. "
                f"Do not treat a probable sanctions match as confirmed "
                f"without sufficient evidence."
            )

            with st.spinner(
                "Investigating alert..."
            ):
                try:
                    result = run_investigation(
                        user=user,
                        query=query,
                    )

                    st.session_state[
                        "alert_investigation_result"
                    ] = result

                    st.session_state[
                        "alert_investigation_active"
                    ] = True

                    # Keep the same result available to the
                    # Audit Trail page.
                    st.session_state[
                        "investigation_result"
                    ] = result

                except Exception as exc:
                    st.session_state[
                        "alert_investigation_result"
                    ] = None

                    st.error(
                        f"Investigation failed: {exc}"
                    )

        # -----------------------------------------------------
        # SHOW INVESTIGATION RESULT
        # -----------------------------------------------------

        if st.session_state.get(
            "alert_investigation_active",
            False,
        ):
            alert_result = st.session_state.get(
                "alert_investigation_result"
            )

            if alert_result:
                st.divider()

                st.subheader(
                    "Alert investigation result"
                )

                display_result(
                    alert_result
                )


# ==================================================================
# AUDIT TRAIL PAGE
# ==================================================================

def display_audit_page() -> None:
    """Render the read-only Audit Trail page."""

    st.header(
        "📋 Audit Trail"
    )

    st.caption(
        "Review the sanitized audit event generated by "
        "the most recent investigation."
    )

    result = st.session_state.get(
        "investigation_result"
    )

    if not result:
        st.info(
            "No investigation has been run in this session yet."
        )

        return

    # ---------------------------------------------------------
    # GET FINAL RESULT SAFELY
    # ---------------------------------------------------------

    final_result = (
        result.get("final_result")
        or {}
    )

    # ---------------------------------------------------------
    # GET AUDIT EVENT
    # ---------------------------------------------------------

    audit_event = final_result.get(
        "audit_event"
    )

    if not audit_event:
        audit_event = result.get(
            "audit_event"
        )

    display_audit_event(
        audit_event
    )




# ==================================================================
# EVALUATION PAGE
# ==================================================================

def display_evaluation_page() -> None:
    """
    Render the evaluation dashboard.

    Uses the existing evaluation cases and evaluator.
    No separate evaluation logic is introduced in the UI.
    """

    st.header(
        "🧪 Evaluation"
    )

    st.caption(
        "Run the AML Investigator evaluation suite and review "
        "case-level pass/fail results."
    )

    # ---------------------------------------------------------
    # EVALUATION OVERVIEW
    # ---------------------------------------------------------

    try:
        cases = load_cases()
    except Exception as exc:
        st.error(
            f"Unable to load evaluation cases: {exc}"
        )
        return

    st.subheader(
        "Evaluation suite"
    )

    st.write(
        f"{len(cases)} evaluation cases are configured."
    )

    st.info(
        "The evaluation suite checks factual retrieval, risk signals, "
        "regulatory evidence, sanctions handling, evidence sufficiency, "
        "RBAC, portfolio scope, and prompt-injection resistance."
    )

    # ---------------------------------------------------------
    # RUN EVALUATION
    # ---------------------------------------------------------

    if st.button(
        "Run Evaluation",
        type="primary",
        width="stretch",
    ):
        results = []

        with st.spinner(
            "Running evaluation suite..."
        ):
            for case in cases:
                result = run_case(case)
                results.append(result)

        st.session_state[
            "evaluation_results"
        ] = results

    # ---------------------------------------------------------
    # LOAD SAVED RESULTS
    # ---------------------------------------------------------

    results = st.session_state.get(
        "evaluation_results",
        [],
    )

    if not results:
        st.info(
            "No evaluation has been run yet. "
            "Click 'Run Evaluation' to start."
        )

        return

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    passed = sum(
        1
        for result in results
        if result.get("passed")
    )

    failed = len(results) - passed

    total = len(results)

    pass_rate = (
        (passed / total) * 100
        if total
        else 0
    )

    st.divider()

    st.subheader(
        "Evaluation summary"
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total cases",
            total,
        )

    with col2:
        st.metric(
            "Passed",
            passed,
        )

    with col3:
        st.metric(
            "Failed",
            failed,
        )

    with col4:
        st.metric(
            "Pass rate",
            f"{pass_rate:.1f}%",
        )

    # ---------------------------------------------------------
    # OVERALL STATUS
    # ---------------------------------------------------------

    if failed == 0:
        st.success(
            "All evaluation cases passed."
        )
    else:
        st.error(
            f"{failed} evaluation case(s) failed."
        )

    # ---------------------------------------------------------
    # CASE TABLE
    # ---------------------------------------------------------

    st.subheader(
        "Evaluation cases"
    )

    rows = []

    for result in results:
        status = (
            "PASS"
            if result.get("passed")
            else "FAIL"
        )

        rows.append(
            {
                "ID": result.get(
                    "id",
                    "UNKNOWN",
                ),
                "Status": status,
                "Case": result.get(
                    "name",
                    "Unnamed",
                ),
            }
        )

    st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
    )

    # ---------------------------------------------------------
    # CASE DETAILS
    # ---------------------------------------------------------

    st.subheader(
        "Case details"
    )

    case_lookup = {
        case.get("id"): case
        for case in cases
    }

    result_lookup = {
        result.get("id"): result
        for result in results
    }

    case_ids = [
        result.get("id")
        for result in results
        if result.get("id")
    ]

    selected_case_id = st.selectbox(
        "Select an evaluation case",
        case_ids,
    )

    selected_result = result_lookup.get(
        selected_case_id
    )

    selected_case = case_lookup.get(
        selected_case_id
    )

    if not selected_result:
        st.warning(
            "No result found for the selected case."
        )
        return

    # ---------------------------------------------------------
    # SELECTED CASE SUMMARY
    # ---------------------------------------------------------

    if selected_result.get("passed"):
        st.success(
            f"{selected_case_id} passed."
        )
    else:
        st.error(
            f"{selected_case_id} failed."
        )

    if selected_case:
        st.write(
            "**Question:**"
        )

        st.code(
            selected_case.get(
                "query",
                "",
            ),
            language="text",
        )

    # ---------------------------------------------------------
    # CHECK RESULTS
    # ---------------------------------------------------------

    checks = selected_result.get(
        "checks",
        [],
    )

    if not checks:
        st.info(
            "No evaluation checks were returned."
        )
    else:
        st.write(
            "**Checks:**"
        )

        check_rows = []

        for check in checks:
            check_name = check[0]
            check_passed = check[1]
            details = check[2]

            check_rows.append(
                {
                    "Check": check_name,
                    "Status": (
                        "PASS"
                        if check_passed
                        else "FAIL"
                    ),
                    "Details": details,
                }
            )

        st.dataframe(
            check_rows,
            width="stretch",
            hide_index=True,
        )

    # ---------------------------------------------------------
    # FAILURE DETAILS
    # ---------------------------------------------------------

    failed_checks = [
        check
        for check in checks
        if not check[1]
    ]

    if failed_checks:
        st.subheader(
            "Failed checks"
        )

        for check_name, _, details in failed_checks:
            st.error(
                f"{check_name}: {details}"
            )

    if selected_result.get("error"):
        st.subheader(
            "Evaluation error"
        )

        st.error(
            selected_result["error"]
        )


# ==================================================================
# SYSTEM PAGE
# ==================================================================

def display_system_page() -> None:
    """Render read-only system and component status."""

    st.header(
        "⚙️ System"
    )

    st.caption(
        "Read-only status information for the AML Investigator prototype."
    )

    # ---------------------------------------------------------
    # APPLICATION STATUS
    # ---------------------------------------------------------

    st.subheader(
        "Application status"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.success(
            "Application running"
        )

    with col2:
        st.write(
            "**Version:** 0.1.0"
        )

    with col3:
        st.write(
            "**Environment:** Prototype"
        )

    st.divider()

    # ---------------------------------------------------------
    # DATABASE STATUS
    # ---------------------------------------------------------

    st.subheader(
        "Database"
    )

    db = SessionLocal()

    try:
        db.execute(
            text("SELECT 1")
        )

        st.success(
            "Database connection healthy."
        )

        table_counts = {}

        tables = [
            "customers",
            "transactions",
            "alerts",
            "sanctions_entities",
            "feedback",
        ]

        for table in tables:
            try:
                count = db.execute(
                    text(
                        f"SELECT COUNT(*) FROM {table}"
                    )
                ).scalar()

                table_counts[table] = count

            except Exception:
                table_counts[table] = None

        rows = [
            {
                "Table": table,
                "Rows": (
                    count
                    if count is not None
                    else "Unavailable"
                ),
            }
            for table, count in table_counts.items()
        ]

        st.dataframe(
            rows,
            width="stretch",
            hide_index=True,
        )

    except Exception as exc:
        st.error(
            f"Database connection failed: {exc}"
        )

    finally:
        db.close()

    st.divider()

    # ---------------------------------------------------------
    # REGULATORY KNOWLEDGE
    # ---------------------------------------------------------

    st.subheader(
        "Regulatory knowledge"
    )

    regulation_file = (
        PROJECT_ROOT
        / "data"
        / "understanding"
        / "regulations"
        / "aml_requirements.yaml"
    )

    if regulation_file.exists():
        try:
            import yaml

            with regulation_file.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = yaml.safe_load(file) or {}

            regulations = data.get(
                "regulations",
                [],
            )

            requirement_count = sum(
                len(
                    regulation.get(
                        "requirements",
                        [],
                    )
                )
                for regulation in regulations
            )

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Regulations",
                    len(regulations),
                )

            with col2:
                st.metric(
                    "Requirements",
                    requirement_count,
                )

            st.success(
                "Regulatory YAML loaded successfully."
            )

        except Exception as exc:
            st.error(
                f"Unable to read regulatory configuration: {exc}"
            )

    else:
        st.warning(
            "Regulatory YAML file was not found."
        )

    st.divider()

    # ---------------------------------------------------------
    # CHROMA STATUS
    # ---------------------------------------------------------

    st.subheader(
        "Regulatory vector index"
    )

    chroma_path = (
        PROJECT_ROOT
        / "data"
        / "chroma"
    )

    if chroma_path.exists():
        try:
            import chromadb

            client = chromadb.PersistentClient(
                path=str(chroma_path)
            )

            collection = client.get_or_create_collection(
                name="aml_regulations"
            )

            count = collection.count()

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Indexed requirements",
                    count,
                )

            with col2:
                st.write(
                    "**Collection:** "
                    "`aml_regulations`"
                )

            if count > 0:
                st.success(
                    "Regulatory vector index is available."
                )
            else:
                st.warning(
                    "Regulatory vector index is empty."
                )

        except Exception as exc:
            st.error(
                f"Vector index check failed: {exc}"
            )

    else:
        st.warning(
            "Chroma data directory was not found."
        )

    st.divider()

    # ---------------------------------------------------------
    # AUTHORIZATION ROLES
    # ---------------------------------------------------------

    st.subheader(
        "Authorization roles"
    )

    role_rows = [
        {
            "Role": Role.CCO.value,
            "Purpose": "Full compliance and investigation access",
        },
        {
            "Role": Role.AML_ANALYST.value,
            "Purpose": "AML investigation and masked customer access",
        },
        {
            "Role": Role.EXTERNAL_AUDITOR.value,
            "Purpose": "Audit, rationale, and evidence access",
        },
        {
            "Role": Role.RELATIONSHIP_MANAGER.value,
            "Purpose": "Assigned-portfolio transaction/customer access",
        },
    ]

    st.dataframe(
        role_rows,
        width="stretch",
        hide_index=True,
    )

    st.divider()

    # ---------------------------------------------------------
    # RISK ENGINE CONFIGURATION
    # ---------------------------------------------------------

    st.subheader(
        "Risk engine configuration"
    )

    risk_rows = [
        {
            "Signal": "HIGH_VALUE_TRANSACTION",
            "Weight": 20,
            "Configuration": "Amount >= 10,000",
        },
        {
            "Signal": "POSSIBLE_STRUCTURING",
            "Weight": 25,
            "Configuration": "2+ transactions in 8,000–10,000 range",
        },
        {
            "Signal": "RAPID_MOVEMENT",
            "Weight": 25,
            "Configuration": "Incoming → outgoing within 180 minutes",
        },
        {
            "Signal": "UNUSUAL_GEOGRAPHY",
            "Weight": 15,
            "Configuration": "Prototype geography configuration",
        },
        {
            "Signal": "MULTIPLE_TRANSACTIONS",
            "Weight": 10,
            "Configuration": "3+ transactions",
        },
    ]

    st.dataframe(
        risk_rows,
        width="stretch",
        hide_index=True,
    )

    st.caption(
        "Risk scoring is deterministic prototype prioritization. "
        "It is not a regulatory determination."
    )


# ==================================================================
# PAGE
# ==================================================================

st.title(
    "AML Investigator"
)

st.caption(
    "Agentic AML and Transaction Monitoring Investigation Platform"
)

st.divider()


# ==================================================================
# SIDEBAR
# ==================================================================

with st.sidebar:
    st.header(
        "Investigation Context"
    )

    role_name = st.selectbox(
        "Role",
        [
            Role.CCO.value,
            Role.AML_ANALYST.value,
            Role.EXTERNAL_AUDITOR.value,
            Role.RELATIONSHIP_MANAGER.value,
        ],
        key="role_selector",
    )

    portfolio_id = None

    if role_name == Role.RELATIONSHIP_MANAGER.value:
        portfolio_id = st.text_input(
            "Portfolio ID",
            value="PORT-002",
            key="portfolio_input",
        )

    st.caption(
        "The selected role is enforced by the existing "
        "backend authorization layer."
    )


# ==================================================================
# USER CONTEXT
# ==================================================================

user = create_user_context(
    role_name=role_name,
    portfolio_id=portfolio_id,
)


# ==================================================================
# MAIN NAVIGATION
# ==================================================================

investigate_tab, alerts_tab, audit_tab, evaluation_tab, system_tab = st.tabs(
    [
        "🔎 Investigate",
        "🚨 Alerts",
        "📋 Audit Trail",
        "📊 Evaluation",
        "⚙️ System",
    ]
)





# ==================================================================
# INVESTIGATE TAB
# ==================================================================

with investigate_tab:

    st.header(
        "Investigate"
    )

    query = st.text_area(
        "Investigation question",
        value=(
            "Why was transaction TXN1042 flagged, and does it violate "
            "any applicable AML requirements?"
        ),
        height=100,
        key="investigation_query",
    )

    if st.button(
        "Investigate",
        type="primary",
        width="stretch",
    ):
        if not query.strip():
            st.warning(
                "Enter an investigation question."
            )

        else:
            st.session_state[
                "alert_investigation_active"
            ] = False

            with st.spinner(
                "Running investigation..."
            ):
                try:
                    result = run_investigation(
                        user=user,
                        query=query.strip(),
                    )

                    st.session_state[
                        "investigation_result"
                    ] = result

                except Exception as exc:
                    st.session_state[
                        "investigation_result"
                    ] = None

                    st.error(
                        f"Investigation failed: {exc}"
                    )

    saved_result = st.session_state.get(
        "investigation_result"
    )

    if (
        saved_result
        and not st.session_state.get(
            "alert_investigation_active",
            False,
        )
    ):
        st.divider()

        display_result(
            saved_result
        )


# ==================================================================
# ALERTS TAB
# ==================================================================

with alerts_tab:

    display_alerts_page(
        user=user
    )


# ==================================================================
# AUDIT TRAIL TAB
# ==================================================================

with audit_tab:

    display_audit_page()


# ==================================================================
# EVALUATION TAB
# ==================================================================

with evaluation_tab:

    display_evaluation_page()


# ==================================================================
# SYSTEM TAB
# ==================================================================

with system_tab:

    display_system_page()
