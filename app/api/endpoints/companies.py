"""
Company management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.schemas import (
    CompanyProfileCreate,
    CompanyProfileUpdate,
    CompanyProfileResponse,
)
from app.services import CompanyService

router = APIRouter(
    prefix="/companies",
    tags=["companies"],
)


@router.post(
    "",
    response_model=CompanyProfileResponse,
    summary="Create Company Profile",
    description="Register a new SME company profile",
)
async def create_company(
    company_data: CompanyProfileCreate,
    db: Session = Depends(get_db),
) -> CompanyProfileResponse:
    """
    Create a new company profile
    
    Args:
        company_data: Company information
        db: Database session
        
    Returns:
        Created company profile
    """
    # Check if company already exists
    existing = CompanyService.get_company_by_name(db, company_data.company_name)
    if existing:
        raise HTTPException(status_code=400, detail="Company already exists")
    
    company = CompanyService.create_company(db, company_data)
    return company


@router.get(
    "/{company_id}",
    response_model=CompanyProfileResponse,
    summary="Get Company Profile",
    description="Retrieve company profile by ID",
)
async def get_company(
    company_id: int,
    db: Session = Depends(get_db),
) -> CompanyProfileResponse:
    """
    Get company profile
    
    Args:
        company_id: Company ID
        db: Database session
        
    Returns:
        Company profile details
    """
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return company


@router.get(
    "",
    response_model=List[CompanyProfileResponse],
    summary="List Companies",
    description="List all registered companies",
)
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> List[CompanyProfileResponse]:
    """
    List all companies
    
    Args:
        skip: Number of companies to skip
        limit: Maximum number of companies to return
        db: Database session
        
    Returns:
        List of company profiles
    """
    companies = CompanyService.list_companies(db, skip=skip, limit=limit)
    return companies


@router.patch(
    "/{company_id}",
    response_model=CompanyProfileResponse,
    summary="Update Company Profile",
    description="Update company profile information",
)
async def update_company(
    company_id: int,
    company_data: CompanyProfileUpdate,
    db: Session = Depends(get_db),
) -> CompanyProfileResponse:
    """
    Update company profile
    
    Args:
        company_id: Company ID
        company_data: Updated company information
        db: Database session
        
    Returns:
        Updated company profile
    """
    company = CompanyService.update_company(db, company_id, company_data)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return company


@router.get(
    "/{company_id}/metrics",
    summary="Get Financial Metrics",
    description="Get key financial metrics for a company",
)
async def get_company_metrics(
    company_id: int,
    db: Session = Depends(get_db),
):
    """
    Get financial metrics for a company
    
    Args:
        company_id: Company ID
        db: Database session
        
    Returns:
        Financial metrics including revenue, expenses, profit margin
    """
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    metrics = CompanyService.calculate_financial_metrics(db, company_id)
    return {
        "company_id": company_id,
        "company_name": company.company_name,
        "metrics": metrics,
    }
