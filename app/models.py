
from datetime import datetime
from app.models_feedback import Feedback

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)

from app.db import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    name = Column(String, nullable=False)
    account_id = Column(String, nullable=False, index=True)
    country = Column(String)
    occupation = Column(String)
    business_type = Column(String)
    risk_rating = Column(String)
    portfolio_id = Column(String, index=True)
    kyc_status = Column(String)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    transaction_id = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    customer_id = Column(
        String,
        nullable=False,
        index=True,
    )

    account_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    transaction_type = Column(String)
    amount = Column(Float)
    currency = Column(String)
    counterparty = Column(String)
    country = Column(String)
    description = Column(Text)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)

    alert_id = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    customer_id = Column(
        String,
        nullable=False,
        index=True,
    )

    transaction_id = Column(
        String,
        nullable=False,
        index=True,
    )

    alert_type = Column(String)
    severity = Column(String)
    status = Column(String)
    created_at = Column(DateTime)
    description = Column(Text)


class SanctionsEntity(Base):
    __tablename__ = "sanctions_entities"

    id = Column(Integer, primary_key=True, index=True)

    entity_id = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    name = Column(String, nullable=False)
    aliases = Column(Text)
    country = Column(String)
    list_name = Column(String)
    match_type = Column(String)
    risk_level = Column(String)

