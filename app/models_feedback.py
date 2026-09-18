from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.db import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False)
    customer_id = Column(String, nullable=True, index=True)
    transaction_id = Column(String, nullable=True, index=True)
    signal = Column(String, nullable=True)
    disposition = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    adjustment = Column(Float, nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )