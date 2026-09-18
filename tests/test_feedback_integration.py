from app.agents.screening_agent import ScreeningAgent
from app.auth.context import UserContext
from app.auth.permissions import Role
from app.db import SessionLocal
from app.feedback.feedback_engine import persist_feedback
from app.models_feedback import Feedback


def analyst():
    return UserContext(
        user_id="analyst-feedback-test",
        role=Role.AML_ANALYST,
    )


def test_screening_agent_uses_customer_feedback():
    db = SessionLocal()

    try:
        # Keep this test isolated from feedback created by previous runs.
        db.query(Feedback).filter(
            Feedback.customer_id == "C102"
        ).delete(
            synchronize_session=False
        )
        db.commit()

        agent = ScreeningAgent(db)

        before = agent.investigate(
            user=analyst(),
            customer_id="C102",
        )

        original_score = before.risk_assessment.score

        persist_feedback(
            db,
            investigation_id=before.investigation_id,
            user_id="analyst-feedback-test",
            customer_id="C102",
            transaction_id=None,
            disposition="TRUE HIT",
            reason="Confirmed suspicious activity.",
        )

        after = agent.investigate(
            user=analyst(),
            customer_id="C102",
        )

        assert after.risk_assessment.original_score == original_score
        assert after.risk_assessment.feedback_adjustment == 10
        assert after.risk_assessment.score == min(
            100,
            original_score + 10,
        )

    finally:
        db.query(Feedback).filter(
            Feedback.customer_id == "C102"
        ).delete(
            synchronize_session=False
        )
        db.commit()
        db.close()


def test_unrelated_customer_feedback_does_not_affect_investigation():
    db = SessionLocal()

    try:
        # Keep this test isolated from feedback created by previous runs.
        db.query(Feedback).filter(
            Feedback.customer_id.in_(["C101", "C102"])
        ).delete(
            synchronize_session=False
        )
        db.commit()

        agent = ScreeningAgent(db)

        before = agent.investigate(
            user=analyst(),
            customer_id="C102",
        )

        original_score = before.risk_assessment.score

        persist_feedback(
            db,
            investigation_id=before.investigation_id,
            user_id="analyst-feedback-test",
            customer_id="C101",
            transaction_id=None,
            disposition="TRUE HIT",
            reason="Feedback belongs to another customer.",
        )

        after = agent.investigate(
            user=analyst(),
            customer_id="C102",
        )

        assert after.risk_assessment.score == original_score
        assert after.risk_assessment.feedback_adjustment == 0

    finally:
        db.query(Feedback).filter(
            Feedback.customer_id.in_(["C101", "C102"])
        ).delete(
            synchronize_session=False
        )
        db.commit()
        db.close()