"""
SME profile model for the BNPL Advisor backend.
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SMEProfile(Base):
    """Core SME profile used for financial decisioning context."""

    __tablename__ = "sme_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    industry: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    monthly_revenue_rm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    monthly_expenses_rm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cash_on_hand_rm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_debt_rm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    credit_score: Mapped[int] = mapped_column(Integer, nullable=False, default=650)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
