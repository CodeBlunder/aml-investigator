from dataclasses import dataclass

from app.auth.permissions import Role


@dataclass(frozen=True)
class UserContext:
    """
    Represents the authenticated user's authorization context.

    portfolio_id is required for Relationship Managers because
    their access is limited to their assigned portfolio.
    """

    user_id: str
    role: Role
    portfolio_id: str | None = None
