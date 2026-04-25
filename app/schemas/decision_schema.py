"""
Decision schemas for BNPL advisor recommendations.
"""
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class DecisionImpactMetrics(BaseModel):
    """Quantifiable impact metrics for recommendation quality."""

    projected_cashflow_change_rm: float
    estimated_interest_savings_rm: float
    estimated_roi_percent: float
    payback_period_months: float
    runway_extension_days: float
    risk_score: float = Field(..., ge=0, le=1)


class DecisionRequest(BaseModel):
    """Input schema for GLM-backed financial decisions."""

    sme_profile_id: int
    purchase_amount_rm: float = Field(..., gt=0)
    purchase_purpose: str = Field(..., min_length=5)
    structured_financial_data: List[Dict[str, Any]] = Field(default_factory=list)
    unstructured_documents: List[str] = Field(default_factory=list)


class DecisionResponse(BaseModel):
    """Output schema for GLM decision results."""

    decision: str = Field(..., description="approve|defer|reject|review")
    recommended_financing: str = Field(..., description="bnpl|traditional|hybrid")
    explanation: str
    action_recommendations: List[str] = Field(default_factory=list)
    impact_metrics: DecisionImpactMetrics
