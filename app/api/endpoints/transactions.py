"""
Transaction management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.schemas import (
    TransactionCreate,
    TransactionBulkCreate,
    TransactionResponse,
)
from app.services import CompanyService, TransactionService

router = APIRouter(
    prefix="/transactions",
    tags=["transactions"],
)


@router.post(
    "",
    response_model=TransactionResponse,
    summary="Create Transaction",
    description="Record a new financial transaction",
)
async def create_transaction(
    transaction_data: TransactionCreate,
    db: Session = Depends(get_db),
) -> TransactionResponse:
    """
    Create a new transaction
    
    Args:
        transaction_data: Transaction details
        db: Database session
        
    Returns:
        Created transaction
    """
    # Validate company exists
    company = CompanyService.get_company(db, transaction_data.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    transaction = TransactionService.create_transaction(db, transaction_data)
    return transaction


@router.post(
    "/bulk",
    response_model=List[TransactionResponse],
    summary="Bulk Upload Transactions",
    description="Import multiple transactions at once",
)
async def bulk_create_transactions(
    bulk_data: TransactionBulkCreate,
    db: Session = Depends(get_db),
) -> List[TransactionResponse]:
    """
    Bulk create transactions
    
    Args:
        bulk_data: Bulk transaction data
        db: Database session
        
    Returns:
        List of created transactions
    """
    # Validate company exists
    company = CompanyService.get_company(db, bulk_data.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    transactions = TransactionService.bulk_create_transactions(db, bulk_data)
    return transactions


@router.get(
    "/company/{company_id}",
    response_model=List[TransactionResponse],
    summary="Get Company Transactions",
    description="Retrieve transaction history for a company",
)
async def get_company_transactions(
    company_id: int,
    days_back: int = Query(90, ge=1, le=365),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> List[TransactionResponse]:
    """
    Get transactions for a company
    
    Args:
        company_id: Company ID
        days_back: Number of days of history to retrieve
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of transactions
    """
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    transactions = TransactionService.get_company_transactions(
        db, company_id, days_back=days_back, skip=skip, limit=limit
    )
    return transactions
