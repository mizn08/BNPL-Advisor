"""
SME request/response schemas.
"""
from datetime import datetime

from pydantic import BaseModel, Field


class SMEProfileCreate(BaseModel):
    """Schema for creating SME profile data."""

    company_name: str = Field(..., min_length=2, max_length=255)
    industry: str = Field(..., min_length=2, max_length=120)
    monthly_revenue_rm: float = Field(..., ge=0)
    monthly_expenses_rm: float = Field(..., ge=0)
    cash_on_hand_rm: float = Field(..., ge=0)
    current_debt_rm: float = Field(0, ge=0)
    credit_score: int = Field(..., ge=300, le=900)


class SMEProfileResponse(SMEProfileCreate):
    """Schema returned for SME profile endpoints."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
