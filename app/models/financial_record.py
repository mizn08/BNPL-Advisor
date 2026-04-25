"""
Financial record model for structured SME financial data.
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FinancialRecord(Base):
    """Structured financial entries such as transactions or ledger rows."""

    __tablename__ = "financial_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sme_profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sme_profiles.id"), nullable=False, index=True
    )
    record_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    amount_rm: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False, default="other")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    counterparty: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    record_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
