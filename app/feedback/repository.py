from sqlalchemy.orm import Session

from app.models_feedback import Feedback


class FeedbackRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, feedback: Feedback) -> Feedback:
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def get_for_customer(
        self,
        customer_id: str,
    ) -> list[Feedback]:
        return (
            self.db.query(Feedback)
            .filter(Feedback.customer_id == customer_id)
            .order_by(Feedback.created_at.desc())
            .all()
        )

    def get_for_transaction(
        self,
        transaction_id: str,
    ) -> list[Feedback]:
        return (
            self.db.query(Feedback)
            .filter(Feedback.transaction_id == transaction_id)
            .order_by(Feedback.created_at.desc())
            .all()
        )