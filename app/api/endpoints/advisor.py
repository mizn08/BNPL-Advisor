"""
BNPL Advisor Endpoints
Core decision intelligence logic for BNPL vs Traditional Financing
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
import json
from pydantic import BaseModel, Field

from app.db import get_db
from app.schemas import (
    GLMAnalysisRequest,
    BNPLRecommendationResponse,
    BNPLApprovalRequest,
)
from app.services import (
    CompanyService,
    TransactionService,
    RecommendationService,
)
from app.services.decision_engine import BNPLDecisionEngine
from app.core.z_ai_client import get_glm_client

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/advisor",
    tags=["BNPL Decision Intelligence"],
)

# Initialize decision engine
decision_engine = BNPLDecisionEngine()


class PurchaseEvaluationRequest(BaseModel):
    """Request payload for a direct SME purchase evaluation."""

    company_name: str = Field(..., description="SME company name")
    industry: str = Field(..., description="SME industry segment")
    monthly_revenue_rm: float = Field(..., gt=0, description="Average monthly revenue in RM")
    monthly_expenses_rm: float = Field(..., ge=0, description="Average monthly expenses in RM")
    cash_on_hand_rm: float = Field(..., ge=0, description="Current available cash balance in RM")
    current_debt_rm: float = Field(0, ge=0, description="Current outstanding debt in RM")
    credit_score: int = Field(..., ge=300, le=900, description="Business credit score")
    purchase_amount_rm: float = Field(..., gt=0, description="Requested purchase amount in RM")
    purchase_purpose: str = Field(..., min_length=5, description="Purpose of the purchase")
    expected_revenue_uplift_percent: float = Field(
        0, ge=0, description="Expected monthly revenue uplift in percent"
    )
    transaction_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Structured financial records such as ledger or transaction rows",
    )
    unstructured_documents: List[str] = Field(
        default_factory=list,
        description="Unstructured text snippets from invoices, contracts, or notes",
    )


class ImpactMetrics(BaseModel):
    """Quantifiable impact metrics returned by GLM."""

    projected_cashflow_change_rm: float
    estimated_roi_percent: float
    payback_period_months: float
    risk_score: float = Field(..., ge=0, le=1)


class PurchaseEvaluationResponse(BaseModel):
    """Structured decision payload for SME purchase recommendation."""

    decision: str = Field(..., description="approve | defer | reject | review")
    explanation: str
    recommended_financing: str = Field(..., description="bnpl | traditional | hybrid")
    action_recommendations: List[str] = Field(default_factory=list)
    impact_metrics: ImpactMetrics


class BNPLProviderOption(BaseModel):
    """Available BNPL option details included in evaluation payload."""

    provider: str
    terms: str
    interest_rate: float = Field(..., ge=0)
    fees: float = Field(0, ge=0)


class EvaluatePurchaseRequest(BaseModel):
    """Request body for /advisor/{sme_id}/evaluate-purchase."""

    purchase_amount: float = Field(..., gt=0)
    purchase_category: str = Field(..., min_length=2)
    supplier_terms: str = Field(..., min_length=2)
    available_bnpl_options: List[BNPLProviderOption] = Field(default_factory=list)


class EvaluatePurchaseResponse(BaseModel):
    """GLM-backed response for financing decision critical path."""

    decision: str
    confidence_score: float = Field(..., ge=0, le=1)
    explanation: str
    quantifiable_impact: Dict[str, Any]


@router.post(
    "/{sme_id}/evaluate-purchase",
    response_model=EvaluatePurchaseResponse,
    summary="Evaluate Purchase Decision",
    description=(
        "Critical-path endpoint that retrieves SME financial history and projections, "
        "formats full purchase context, and delegates the decision to Z.AI GLM."
    ),
)
async def evaluate_purchase_for_sme(
    sme_id: int,
    request: EvaluatePurchaseRequest,
    db: Session = Depends(get_db),
) -> EvaluatePurchaseResponse:
    """Evaluate whether BNPL, traditional financing, or cash is the right choice."""
    company = CompanyService.get_company(db, sme_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    transactions = TransactionService.get_company_transactions(
        db,
        sme_id,
        days_back=180,
        skip=0,
        limit=3000,
    )
    transaction_history = [
        {
            "transaction_date": tx.transaction_date.isoformat() if tx.transaction_date else None,
            "transaction_type": tx.transaction_type,
            "amount": tx.amount,
            "category": tx.category or "other",
        }
        for tx in transactions
    ]
    financial_metrics = CompanyService.calculate_financial_metrics(db, sme_id)

    prompt = f"""
You are Z.AI GLM, the core financial decision engine for SME BNPL advisory.
Decide the best financing option for this purchase using the full context.

SME PROFILE
- SME ID: {sme_id}
- Company Name: {company.company_name}
- Industry: {company.industry}
- Credit Score: {company.credit_score or 700}
- Annual Revenue (RM): {company.annual_revenue or 0}

CURRENT FINANCIAL CONTEXT
{json.dumps(financial_metrics, default=str)}

HISTORICAL TRANSACTIONS (LAST 180 DAYS)
{json.dumps(transaction_history, default=str)}

PURCHASE DETAILS
- Purchase Amount (RM): {request.purchase_amount}
- Purchase Category: {request.purchase_category}
- Supplier Terms: {request.supplier_terms}
- BNPL Options: {json.dumps([option.model_dump() for option in request.available_bnpl_options])}

INSTRUCTIONS
1) Provide ONE clear decision sentence (example: "Recommend BNPL via Provider A").
2) Include confidence_score from 0.0 to 1.0.
3) Explain the reasoning clearly in plain business language.
4) Quantify impact with cash preservation and ROI increase.
5) Be conservative with risk assumptions.

Return STRICT JSON with this shape:
{{
  "decision": "Recommend BNPL via Provider A",
  "confidence_score": 0.92,
  "explanation": "clear rationale",
  "quantifiable_impact": {{
    "cash_flow_preserved": number,
    "projected_roi_increase": "x.x%"
  }}
}}
"""
    try:
        glm_client = get_glm_client()
        result = await glm_client.evaluate_purchase(prompt)

        impact = result.get("quantifiable_impact") or result.get("impact_metrics") or {}
        cash_flow_preserved = float(
            impact.get("cash_flow_preserved")
            or impact.get("projected_cashflow_change_rm")
            or 0.0
        )
        projected_roi_increase = impact.get("projected_roi_increase")
        if projected_roi_increase is None:
            roi_fallback = impact.get("revenue_capacity_uplift_percent", 0.0) or 0.0
            projected_roi_increase = f"{float(roi_fallback):.1f}%"

        quantifiable_impact = {
            "cash_flow_preserved": cash_flow_preserved,
            "projected_roi_increase": str(projected_roi_increase),
        }

        return EvaluatePurchaseResponse(
            decision=str(
                result.get("decision")
                or f"Recommend {str(result.get('financing_decision') or 'traditional').upper()}"
            ),
            confidence_score=float(result.get("confidence_score", 0.7) or 0.7),
            explanation=str(
                result.get(
                    "explanation",
                    "Financing recommendation generated by Z.AI GLM from SME financial context.",
                )
            ),
            quantifiable_impact=quantifiable_impact,
        )
    except Exception as e:
        logger.error("Error during /advisor/%s/evaluate-purchase: %s", sme_id, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to evaluate purchase: {str(e)}")


@router.post(
    "/evaluate-purchase",
    response_model=PurchaseEvaluationResponse,
    summary="Evaluate SME Purchase",
    description=(
        "Evaluate an SME purchase using financial context and Z.AI GLM, "
        "returning a decision, explanation, and impact metrics."
    ),
)
async def evaluate_purchase(
    request: PurchaseEvaluationRequest,
):
    """
    Evaluate whether an SME should proceed with a purchase.

    This endpoint formats a finance-specific prompt from SME context
    and delegates reasoning to the Z.AI GLM client wrapper.
    """
    try:
        prompt = f"""SME purchase evaluation. Return ONLY JSON.
Company: {request.company_name} ({request.industry}). Revenue RM{request.monthly_revenue_rm:.0f}/mo, Expenses RM{request.monthly_expenses_rm:.0f}/mo, Cash RM{request.cash_on_hand_rm:.0f}, Debt RM{request.current_debt_rm:.0f}, Credit {request.credit_score}. Purchase RM{request.purchase_amount_rm:.0f} for {request.purchase_purpose}. Expected uplift {request.expected_revenue_uplift_percent:.0f}%.
JSON schema: {{"decision":"approve|defer|reject","recommended_financing":"bnpl|traditional|hybrid","explanation":"2 sentences","action_recommendations":["a1","a2","a3"],"impact_metrics":{{"projected_cashflow_change_rm":number,"estimated_roi_percent":number,"payback_period_months":number,"risk_score":0to1}}}}"""
        glm_client = get_glm_client()
        result = await glm_client.evaluate_purchase(prompt)
        return PurchaseEvaluationResponse(**result)
    except Exception as e:
        logger.error("Error during /evaluate-purchase: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to evaluate purchase: {str(e)}",
        )


@router.post(
    "/analyze",
    response_model=BNPLRecommendationResponse,
    summary="Analyze Financing Decision",
    description="Get AI-powered BNPL vs Traditional Financing recommendation",
)
async def analyze_financing_decision(
    request: GLMAnalysisRequest,
    db: Session = Depends(get_db),
) -> BNPLRecommendationResponse:
    """
    Get BNPL recommendation using Z.AI GLM
    
    This is the core decision intelligence endpoint that:
    1. Validates company financial data
    2. Processes transactions into metrics
    3. Calls Z.AI GLM with full financial context
    4. Returns recommendation with clear rationale
    5. Stores recommendation for audit trail
    
    Args:
        request: Financial analysis request with transaction details
        db: Database session
        
    Returns:
        BNPL recommendation with decision rationale and quantified impact
    """
    
    # Validate company exists
    company = CompanyService.get_company(db, request.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        # Get company transactions for analysis
        transactions = TransactionService.get_company_transactions(
            db,
            request.company_id,
            days_back=90,
            skip=0,
            limit=1000,
        )
        
        # Convert to dict for processing
        tx_dicts = [
            {
                "transaction_date": tx.transaction_date,
                "transaction_type": tx.transaction_type,
                "amount": tx.amount,
                "category": tx.category or "other",
            }
            for tx in transactions
        ]
        
        # Call decision engine (orchestrates data processing + GLM)
        glm_recommendation = await decision_engine.analyze_financing_decision(
            company_id=request.company_id,
            company_profile={
                "company_name": company.company_name,
                "industry": company.industry,
                "credit_score": company.credit_score or 700,
                "annual_revenue": company.annual_revenue or 0,
            },
            transactions=tx_dicts,
            cash_balance=request.current_cash_balance,
            transaction_amount=request.transaction_amount,
            transaction_purpose=request.transaction_purpose,
            current_debt=request.current_debt or 0,
            credit_score=request.credit_score or 700,
        )
        
        # Create recommendation record in database
        db_rec = RecommendationService.create_recommendation(
            db,
            company_id=request.company_id,
            recommendation_type=glm_recommendation.get("recommendation_type"),
            transaction_amount=request.transaction_amount,
            transaction_purpose=request.transaction_purpose,
        )
        
        # Update with GLM response
        RecommendationService.update_recommendation_from_glm(
            db,
            db_rec.id,
            glm_recommendation,
        )
        
        logger.info(
            f"Financing analysis completed for company={request.company_id}, "
            f"amount=RM {request.transaction_amount:,.2f}, "
            f"recommendation={glm_recommendation.get('recommendation_type')}"
        )
        
        # Return formatted response
        return BNPLRecommendationResponse(
            id=db_rec.id,
            company_id=request.company_id,
            recommendation_type=glm_recommendation.get("recommendation_type"),
            transaction_amount=request.transaction_amount,
            transaction_purpose=request.transaction_purpose,
            recommendation_rationale=glm_recommendation.get("recommendation_rationale"),
            estimated_interest_savings=glm_recommendation.get("estimated_interest_savings"),
            estimated_cash_flow_improvement=glm_recommendation.get("estimated_cash_flow_improvement"),
            revenue_capacity_increase=glm_recommendation.get("revenue_capacity_increase"),
            recommended_tenor_days=glm_recommendation.get("recommended_tenor_days"),
            alternative_option=glm_recommendation.get("alternative_option"),
            confidence_score=glm_recommendation.get("confidence_score"),
            is_approved=False,
            implementation_status="pending",
            created_at=db_rec.created_at,
            updated_at=db_rec.updated_at,
        )
        
    except Exception as e:
        logger.error(f"Error analyzing financing decision: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get(
    "/recommendation/{recommendation_id}",
    response_model=BNPLRecommendationResponse,
    summary="Get Recommendation",
    description="Retrieve a specific BNPL recommendation",
)
async def get_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
) -> BNPLRecommendationResponse:
    """Get recommendation details with full decision context"""
    recommendation = RecommendationService.get_recommendation(db, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    return recommendation


@router.get(
    "/company/{company_id}/recommendations",
    response_model=List[BNPLRecommendationResponse],
    summary="List Company Recommendations",
    description="Get all BNPL recommendations for a company",
)
async def list_company_recommendations(
    company_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> List[BNPLRecommendationResponse]:
    """
    Get all recommendations for a company
    
    Useful for reviewing decision history and patterns
    """
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    recommendations = RecommendationService.list_company_recommendations(
        db, company_id, skip=skip, limit=limit
    )
    return recommendations


@router.post(
    "/recommendation/{recommendation_id}/approve",
    response_model=BNPLRecommendationResponse,
    summary="Approve Recommendation",
    description="Approve a BNPL recommendation for implementation",
)
async def approve_recommendation(
    recommendation_id: int,
    approval_data: BNPLApprovalRequest,
    db: Session = Depends(get_db),
) -> BNPLRecommendationResponse:
    """
    Approve or reject a recommendation
    
    After approval, recommendation moves to implementation phase
    """
    recommendation = RecommendationService.approve_recommendation(
        db, recommendation_id, approval_data.approved
    )
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    status = "approved" if approval_data.approved else "rejected"
    logger.info(
        f"Recommendation {recommendation_id} {status}. "
        f"Notes: {approval_data.approval_notes}"
    )
    
    return recommendation


@router.post(
    "/quick-analysis",
    summary="Quick BNPL Suitability Check",
    description="Fast pre-qualification for BNPL suitability",
)
async def quick_bnpl_suitability_check(
    company_id: int,
    transaction_amount: float,
    db: Session = Depends(get_db),
):
    """
    Quick pre-qualification check for BNPL suitability
    
    Returns immediate assessment before full analysis
    """
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get financial metrics
    metrics = CompanyService.calculate_financial_metrics(db, company_id)
    
    # Quick suitability assessment
    suitability = BNPLDecisionEngine.evaluate_bnpl_suitability(
        metrics,
        transaction_amount,
    )
    
    return {
        "company_id": company_id,
        "company_name": company.company_name,
        "transaction_amount": transaction_amount,
        "bnpl_suitability": suitability,
        "financial_metrics": metrics,
    }


@router.get(
    "/recommendation/{recommendation_id}/summary",
    summary="Get Recommendation Summary",
    description="Get human-readable recommendation summary",
)
async def get_recommendation_summary(
    recommendation_id: int,
    db: Session = Depends(get_db),
):
    """
    Get formatted text summary of recommendation
    
    Useful for reports and presentations
    """
    recommendation = RecommendationService.get_recommendation(db, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    # Build summary dict
    summary_data = {
        "id": recommendation.id,
        "company_id": recommendation.company_id,
        "recommendation_type": recommendation.recommendation_type,
        "transaction_amount": recommendation.transaction_amount,
        "transaction_purpose": recommendation.transaction_purpose,
        "recommendation_rationale": recommendation.recommendation_rationale,
        "estimated_interest_savings": recommendation.estimated_interest_savings,
        "estimated_cash_flow_improvement": recommendation.estimated_cash_flow_improvement,
        "recommended_tenor_days": recommendation.recommended_tenor_days,
        "confidence_score": recommendation.confidence_score,
        "implementation_status": recommendation.implementation_status,
    }
    
    # Generate formatted summary
    summary_text = BNPLDecisionEngine.format_recommendation_summary(summary_data)
    
    return {
        "recommendation_id": recommendation_id,
        "summary": summary_text,
        "data": summary_data,
    }
