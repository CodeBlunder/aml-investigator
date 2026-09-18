from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.auth.context import UserContext
from app.auth.permissions import Role, has_permission
from app.models import Alert, Customer, SanctionsEntity, Transaction


BASE_DIR = Path(__file__).resolve().parents[2]


COUNTRY_ALIASES = {
    "uae": "United Arab Emirates",
    "u.a.e.": "United Arab Emirates",
    "united arab emirates": "United Arab Emirates",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "usa": "United States",
    "u.s.a.": "United States",
    "us": "United States",
    "u.s.": "United States",
}


def normalize_country(country: str) -> str:
    if not country:
        return ""

    normalized = country.strip().lower()

    return COUNTRY_ALIASES.get(
        normalized,
        country.strip(),
    )


def get_transaction(
    db: Session,
    user: UserContext,
    transaction_id: str,
) -> dict:
    if not has_permission(user.role, "transactions"):
        return {
            "success": False,
            "error": "ACCESS_DENIED",
            "message": (
                "The current role is not authorized "
                "to access transactions."
            ),
        }

    transaction = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction_id)
        .first()
    )

    if transaction is None:
        return {
            "success": False,
            "error": "NOT_FOUND",
            "message": f"Transaction {transaction_id} was not found.",
        }

    if user.role == Role.RELATIONSHIP_MANAGER:
        customer = (
            db.query(Customer)
            .filter(Customer.customer_id == transaction.customer_id)
            .first()
        )

        if customer is None:
            return {
                "success": False,
                "error": "NOT_FOUND",
                "message": (
                    "The customer associated with this "
                    "transaction was not found."
                ),
            }

        if user.portfolio_id != customer.portfolio_id:
            return {
                "success": False,
                "error": "ACCESS_DENIED",
                "message": (
                    "The transaction is outside the user's "
                    "assigned portfolio."
                ),
            }

    return {
        "success": True,
        "data": _transaction_to_dict(transaction),
    }


def search_transactions(
    db: Session,
    user: UserContext,
    customer_id: str | None = None,
    account_id: str | None = None,
    country: str | None = None,
    transaction_type: str | None = None,
    start_date=None,
    end_date=None,
    max_results: int = 50,
) -> dict:
    if not has_permission(user.role, "transactions"):
        return {
            "success": False,
            "error": "ACCESS_DENIED",
            "message": (
                "The current role is not authorized "
                "to access transactions."
            ),
        }

    if max_results < 1 or max_results > 100:
        return {
            "success": False,
            "error": "INVALID_INPUT",
            "message": "max_results must be between 1 and 100.",
        }

    query = db.query(Transaction)

    if customer_id:
        query = query.filter(
            Transaction.customer_id == customer_id
        )

    if account_id:
        query = query.filter(
            Transaction.account_id == account_id
        )

    if country:
        query = query.filter(
            Transaction.country == normalize_country(country)
        )

    if transaction_type:
        query = query.filter(
            Transaction.transaction_type == transaction_type
        )

    if start_date:
        query = query.filter(
            Transaction.timestamp >= start_date
        )

    if end_date:
        query = query.filter(
            Transaction.timestamp <= end_date
        )

    query = (
        query
        .order_by(Transaction.timestamp.asc())
        .limit(max_results)
    )

    transactions = query.all()

    if user.role == Role.RELATIONSHIP_MANAGER:
        customer_ids = {
            transaction.customer_id
            for transaction in transactions
        }

        if customer_ids:
            customers = (
                db.query(Customer)
                .filter(
                    Customer.customer_id.in_(customer_ids)
                )
                .all()
            )

            allowed_customer_ids = {
                customer.customer_id
                for customer in customers
                if customer.portfolio_id == user.portfolio_id
            }

            transactions = [
                transaction
                for transaction in transactions
                if transaction.customer_id in allowed_customer_ids
            ]

    return {
        "success": True,
        "count": len(transactions),
        "filters": {
            "customer_id": customer_id,
            "account_id": account_id,
            "country": country,
            "transaction_type": transaction_type,
            "start_date": (
                start_date.isoformat()
                if start_date
                else None
            ),
            "end_date": (
                end_date.isoformat()
                if end_date
                else None
            ),
            "max_results": max_results,
        },
        "transactions": [
            _transaction_to_dict(transaction)
            for transaction in transactions
        ],
    }


def _transaction_to_dict(transaction: Transaction) -> dict:
    return {
        "transaction_id": transaction.transaction_id,
        "customer_id": transaction.customer_id,
        "account_id": transaction.account_id,
        "timestamp": (
            transaction.timestamp.isoformat()
            if transaction.timestamp
            else None
        ),
        "transaction_type": transaction.transaction_type,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "counterparty": transaction.counterparty,
        "country": transaction.country,
        "description": transaction.description,
    }


def mask_name(name: str) -> str:
    parts = name.split()

    masked_parts = []

    for part in parts:
        if not part:
            continue

        masked_parts.append(
            part[0] + ("*" * (len(part) - 1))
        )

    return " ".join(masked_parts)


def get_customer(
    db: Session,
    user: UserContext,
    customer_id: str,
) -> dict:
    has_full_access = has_permission(
        user.role,
        "customer_pii",
    )

    has_masked_access = has_permission(
        user.role,
        "customer_masked",
    )

    if not has_full_access and not has_masked_access:
        return {
            "success": False,
            "error": "ACCESS_DENIED",
            "message": (
                "The current role is not authorized "
                "to access customer data."
            ),
        }

    customer = (
        db.query(Customer)
        .filter(Customer.customer_id == customer_id)
        .first()
    )

    if customer is None:
        return {
            "success": False,
            "error": "NOT_FOUND",
            "message": f"Customer {customer_id} was not found.",
        }

    if user.role == Role.RELATIONSHIP_MANAGER:
        if user.portfolio_id != customer.portfolio_id:
            return {
                "success": False,
                "error": "ACCESS_DENIED",
                "message": (
                    "The customer is outside the user's "
                    "assigned portfolio."
                ),
            }

    customer_data = {
        "customer_id": customer.customer_id,
        "name": customer.name,
        "account_id": customer.account_id,
        "country": customer.country,
        "occupation": customer.occupation,
        "business_type": customer.business_type,
        "risk_rating": customer.risk_rating,
        "portfolio_id": customer.portfolio_id,
        "kyc_status": customer.kyc_status,
    }

    if not has_full_access:
        customer_data["name"] = mask_name(customer.name)

    return {
        "success": True,
        "data": customer_data,
    }


def get_alert(
    db: Session,
    user: UserContext,
    alert_id: str,
) -> dict:
    if not has_permission(user.role, "alerts"):
        return {
            "success": False,
            "error": "ACCESS_DENIED",
            "message": (
                "The current role is not authorized "
                "to access alerts."
            ),
        }

    alert = (
        db.query(Alert)
        .filter(Alert.alert_id == alert_id)
        .first()
    )

    if alert is None:
        return {
            "success": False,
            "error": "NOT_FOUND",
            "message": f"Alert {alert_id} was not found.",
        }

    if user.role == Role.RELATIONSHIP_MANAGER:
        customer = (
            db.query(Customer)
            .filter(Customer.customer_id == alert.customer_id)
            .first()
        )

        if customer is None:
            return {
                "success": False,
                "error": "NOT_FOUND",
                "message": (
                    "The customer associated with this "
                    "alert was not found."
                ),
            }

        if user.portfolio_id != customer.portfolio_id:
            return {
                "success": False,
                "error": "ACCESS_DENIED",
                "message": (
                    "The alert is outside the user's "
                    "assigned portfolio."
                ),
            }

    return {
        "success": True,
        "data": {
            "alert_id": alert.alert_id,
            "customer_id": alert.customer_id,
            "transaction_id": alert.transaction_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "status": alert.status,
            "created_at": (
                alert.created_at.isoformat()
                if alert.created_at
                else None
            ),
            "description": alert.description,
        },
    }


def search_sanctions(
    db: Session,
    user: UserContext,
    name: str,
) -> dict:
    if not has_permission(user.role, "sanctions"):
        return {
            "success": False,
            "error": "ACCESS_DENIED",
            "message": (
                "The current role is not authorized "
                "to access sanctions data."
            ),
        }

    if not name or not name.strip():
        return {
            "success": False,
            "error": "INVALID_INPUT",
            "message": "A non-empty name is required.",
        }

    search_term = name.strip().lower()

    entities = db.query(SanctionsEntity).all()

    matches = []

    for entity in entities:
        entity_name = (entity.name or "").lower()

        aliases = []

        if entity.aliases:
            aliases = [
                alias.strip().lower()
                for alias in entity.aliases.split(",")
                if alias.strip()
            ]

        matched_on = None

        if search_term == entity_name:
            matched_on = "name"

        elif search_term in entity_name:
            matched_on = "name_partial"

        elif search_term in aliases:
            matched_on = "alias"

        elif any(
            search_term in alias
            for alias in aliases
        ):
            matched_on = "alias_partial"

        if matched_on:
            matches.append(
                {
                    "entity_id": entity.entity_id,
                    "name": entity.name,
                    "aliases": entity.aliases,
                    "country": entity.country,
                    "list_name": entity.list_name,
                    "match_type": entity.match_type,
                    "risk_level": entity.risk_level,
                    "matched_on": matched_on,
                }
            )

    return {
        "success": True,
        "query": name,
        "match_count": len(matches),
        "matches": matches,
    }


def search_regulations(
    user: UserContext,
    topic: str,
) -> dict:
    """
    Search the structured regulatory understanding layer.

    Natural-language topics such as "unusual geography" are
    normalized to match YAML applicability values such as
    "unusual_geography".
    """

    if not has_permission(user.role, "transactions"):
        return {
            "success": False,
            "error": "User is not authorized to search regulatory evidence.",
        }

    if not topic or not topic.strip():
        return {
            "success": False,
            "error": "Regulatory search topic is required.",
        }

    regulations_path = (
        BASE_DIR
        / "data"
        / "understanding"
        / "regulations"
        / "aml_requirements.yaml"
    )

    if not regulations_path.exists():
        return {
            "success": False,
            "error": "Regulatory understanding file was not found.",
        }

    with regulations_path.open("r", encoding="utf-8") as file:
        regulatory_data = yaml.safe_load(file) or {}

    normalized_topic = topic.strip().lower()
    normalized_topic_key = normalized_topic.replace(" ", "_")

    matches = []

    for regulation in regulatory_data.get("regulations", []):
        for requirement in regulation.get("requirements", []):
            applicability = [
                str(item).strip().lower()
                for item in requirement.get("applicability", [])
            ]

            applicability_values = set(applicability)

            searchable_text = " ".join(
                [
                    str(requirement.get("topic", "")),
                    str(requirement.get("text", "")),
                    " ".join(applicability),
                ]
            ).lower()

            if (
                normalized_topic in searchable_text
                or normalized_topic_key in applicability_values
            ):
                matches.append(
                    {
                        "regulation_id": regulation.get("regulation_id"),
                        "title": regulation.get("title"),
                        "jurisdiction": regulation.get("jurisdiction"),
                        "source": regulation.get("source"),
                        "source_document": regulation.get("source_document"),
                        "requirement_id": requirement.get("requirement_id"),
                        "requirement_topic": requirement.get("topic"),
                        "requirement_text": requirement.get("text"),
                        "applicability": requirement.get(
                            "applicability",
                            [],
                        ),
                    }
                )

    return {
        "success": True,
        "query": topic,
        "match_count": len(matches),
        "matches": matches,
    }

def find_alerts(
    db: Session,
    user: UserContext,
    customer_id: str | None = None,
    transaction_id: str | None = None,
) -> dict:
    """
    Find alerts associated with a customer and/or transaction.

    Access is controlled through the same alert permission and
    relationship-manager portfolio restrictions as get_alert().
    """

    if not has_permission(user.role, "alerts"):
        return {
            "success": False,
            "error": "ACCESS_DENIED",
            "message": (
                "The current role is not authorized "
                "to access alerts."
            ),
        }

    if not customer_id and not transaction_id:
        return {
            "success": False,
            "error": "INVALID_INPUT",
            "message": (
                "customer_id or transaction_id is required."
            ),
        }

    query = db.query(Alert)

    if customer_id:
        query = query.filter(
            Alert.customer_id == customer_id
        )

    if transaction_id:
        query = query.filter(
            Alert.transaction_id == transaction_id
        )

    alerts = (
        query
        .order_by(Alert.created_at.asc())
        .all()
    )

    results = []

    for alert in alerts:
        if user.role == Role.RELATIONSHIP_MANAGER:
            customer = (
                db.query(Customer)
                .filter(
                    Customer.customer_id
                    == alert.customer_id
                )
                .first()
            )

            if customer is None:
                continue

            if user.portfolio_id != customer.portfolio_id:
                continue

        results.append(
            {
                "alert_id": alert.alert_id,
                "customer_id": alert.customer_id,
                "transaction_id": alert.transaction_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "status": alert.status,
                "created_at": (
                    alert.created_at.isoformat()
                    if alert.created_at
                    else None
                ),
                "description": alert.description,
            }
        )

    return {
        "success": True,
        "count": len(results),
        "alerts": results,
    }
