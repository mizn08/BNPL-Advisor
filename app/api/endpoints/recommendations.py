"""
BNPL Recommendation endpoints
Core decision intelligence API
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List
import logging

from app.db import get_db
from app.schemas import (
    GLMAnalysisRequest,
    BNPLRecommendationResponse,
    BNPLApprovalRequest,
)
from app.services import (
    CompanyService,
    RecommendationService,
    get_glm_recommendation,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
)


@router.post(
    "/analyze",
    response_model=BNPLRecommendationResponse,
    summary="Analyze Financing Options",
    description="Get GLM-powered recommendation for BNPL vs Traditional Financing",
)
async def analyze_financing_decision(
    request: GLMAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> BNPLRecommendationResponse:
    """
    Analyze financing decision using Z.AI's GLM
    
    This endpoint:
    1. Validates company financial data
    2. Calls GLM with comprehensive financial context
    3. Returns BNPL recommendation with clear rationale
    4. Stores recommendation in database for audit trail
    
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
        # Get GLM recommendation (CRITICAL PATH)
        glm_response = await get_glm_recommendation(
            request=request,
            company_name=company.company_name,
            industry=company.industry,
        )
        
        # Create recommendation record in database
        rec_data = {
            "company_id": request.company_id,
            "recommendation_type": glm_response.recommendation_type,
            "transaction_amount": request.transaction_amount,
            "transaction_purpose": request.transaction_purpose,
            "recommendation_rationale": glm_response.recommendation_rationale,
            "estimated_interest_savings": glm_response.estimated_interest_savings,
            "estimated_cash_flow_improvement": glm_response.estimated_cash_flow_improvement,
            "revenue_capacity_increase": glm_response.revenue_capacity_increase,
            "recommended_tenor_days": glm_response.recommended_tenor_days,
            "payment_schedule": glm_response.payment_schedule,
            "alternative_option": glm_response.alternative_option,
            "alternative_rationale": glm_response.alternative_rationale,
            "confidence_score": glm_response.confidence_score,
        }
        
        db_rec = RecommendationService.create_recommendation(db, request)
        RecommendationService.update_recommendation_from_glm(db, db_rec.id, rec_data)
        
        logger.info(
            f"Financing analysis completed for company={request.company_id}, "
            f"amount=RM {request.transaction_amount:,.2f}, "
            f"recommendation={glm_response.recommendation_type}"
        )
        
        return BNPLRecommendationResponse(
            id=db_rec.id,
            company_id=request.company_id,
            recommendation_type=glm_response.recommendation_type,
            transaction_amount=request.transaction_amount,
            transaction_purpose=request.transaction_purpose,
            recommendation_rationale=glm_response.recommendation_rationale,
            estimated_interest_savings=glm_response.estimated_interest_savings,
            estimated_cash_flow_improvement=glm_response.estimated_cash_flow_improvement,
            revenue_capacity_increase=glm_response.revenue_capacity_increase,
            recommended_tenor_days=glm_response.recommended_tenor_days,
            alternative_option=glm_response.alternative_option,
            confidence_score=glm_response.confidence_score,
            is_approved=False,
            implementation_status="pending",
            created_at=db_rec.created_at,
            updated_at=db_rec.updated_at,
        )
        
    except Exception as e:
        logger.error(f"Error analyzing financing decision: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get(
    "/{recommendation_id}",
    response_model=BNPLRecommendationResponse,
    summary="Get Recommendation",
    description="Retrieve a specific BNPL recommendation",
)
async def get_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
) -> BNPLRecommendationResponse:
    """
    Get recommendation details
    
    Args:
        recommendation_id: Recommendation ID
        db: Database session
        
    Returns:
        Recommendation details with GLM analysis
    """
    recommendation = RecommendationService.get_recommendation(db, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    return recommendation


@router.get(
    "/company/{company_id}",
    response_model=List[BNPLRecommendationResponse],
    summary="List Company Recommendations",
    description="Get all BNPL recommendations for a company",
)
async def list_company_recommendations(
    company_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[BNPLRecommendationResponse]:
    """
    List all recommendations for a company
    
    Args:
        company_id: Company ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of recommendations
    """
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    recommendations = RecommendationService.list_company_recommendations(
        db, company_id, skip=skip, limit=limit
    )
    return recommendations


@router.post(
    "/{recommendation_id}/approve",
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
    
    Args:
        recommendation_id: Recommendation ID
        approval_data: Approval decision
        db: Database session
        
    Returns:
        Updated recommendation with approval status
    """
    recommendation = RecommendationService.approve_recommendation(
        db, recommendation_id, approval_data.approved
    )
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    status = "approved" if approval_data.approved else "rejected"
    logger.info(f"Recommendation {recommendation_id} {status}")
    
    return recommendation
