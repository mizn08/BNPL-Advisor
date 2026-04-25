"""
SME Profile and Data Ingestion Endpoints
Handles company registration and financial data ingestion
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from io import BytesIO
import pandas as pd
import numpy as np
from PyPDF2 import PdfReader

from app.db import get_db
from app.schemas import (
    CompanyProfileCreate,
    CompanyProfileUpdate,
    CompanyProfileResponse,
    TransactionCreate,
    TransactionBulkCreate,
    TransactionResponse,
)
from app.services import CompanyService, TransactionService, FinancialMetricsCalculator
from app.services.data_processor import DataProcessor
from app.services.document_processor import DocumentProcessor
from app.schemas.file_upload import FileUploadResponse, MetricsImportResponse
from app.models import Transaction, FinancialDocument, DocumentType

router = APIRouter(
    prefix="/sme",
    tags=["SME Management"],
)


def _sanitize_for_json(obj):
    """Recursively convert numpy scalar types to native Python for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def _normalize_transaction_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize uploaded transaction columns to the internal schema."""
    normalized = df.copy()
    normalized.columns = [str(col).strip().lower() for col in normalized.columns]

    normalized = normalized.rename(
        columns={
            "date": "transaction_date",
            "txn_date": "transaction_date",
            "type": "transaction_type",
            "txn_type": "transaction_type",
            "value": "amount",
        }
    )

    if "amount" not in normalized.columns or "transaction_type" not in normalized.columns:
        raise ValueError("Structured file must include amount and transaction_type columns")

    if "transaction_date" not in normalized.columns:
        normalized["transaction_date"] = datetime.utcnow()

    normalized["transaction_date"] = pd.to_datetime(
        normalized["transaction_date"], errors="coerce"
    ).fillna(datetime.utcnow())
    normalized["amount"] = pd.to_numeric(normalized["amount"], errors="coerce").fillna(0)

    if "category" not in normalized.columns:
        normalized["category"] = "other"
    if "description" not in normalized.columns:
        normalized["description"] = ""
    if "counterparty" not in normalized.columns:
        normalized["counterparty"] = ""
    if "reference_number" not in normalized.columns:
        normalized["reference_number"] = None

    normalized["transaction_type"] = (
        normalized["transaction_type"].astype(str).str.strip().str.lower()
    )
    return normalized


# ============ Company Profile Endpoints ============

@router.post(
    "/register",
    response_model=CompanyProfileResponse,
    summary="Register SME Company",
    description="Register a new SME company profile",
)
async def register_company(
    company_data: CompanyProfileCreate,
    db: Session = Depends(get_db),
) -> CompanyProfileResponse:
    """
    Register a new company in Z.AI system
    
    Captures essential company information needed for financial analysis
    """
    # Check if company already exists
    existing = CompanyService.get_company_by_name(db, company_data.company_name)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Company '{company_data.company_name}' already registered"
        )
    
    company = CompanyService.create_company(db, company_data)
    return company


@router.get(
    "/profile/{company_id}",
    response_model=CompanyProfileResponse,
    summary="Get Company Profile",
    description="Retrieve company profile and metadata",
)
async def get_company_profile(
    company_id: int,
    db: Session = Depends(get_db),
) -> CompanyProfileResponse:
    """Get company profile by ID"""
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.patch(
    "/profile/{company_id}",
    response_model=CompanyProfileResponse,
    summary="Update Company Profile",
    description="Update company information",
)
async def update_company_profile(
    company_id: int,
    company_data: CompanyProfileUpdate,
    db: Session = Depends(get_db),
) -> CompanyProfileResponse:
    """Update company profile information"""
    company = CompanyService.update_company(db, company_id, company_data)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.get(
    "/companies",
    response_model=List[CompanyProfileResponse],
    summary="List All Companies",
    description="List all registered companies",
)
async def list_all_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> List[CompanyProfileResponse]:
    """List all registered companies with pagination"""
    return CompanyService.list_companies(db, skip=skip, limit=limit)


# ============ Financial Data Ingestion Endpoints ============

@router.post(
    "/{sme_id}/upload-financials",
    summary="Upload Financial Data",
    description=(
        "Accept structured (CSV/JSON cash flow) and unstructured (PDF invoices) files, "
        "clean and normalize data with pandas, compute baseline metrics, and store records."
    ),
)
async def upload_financials(
    sme_id: int,
    structured_file: UploadFile | None = File(
        default=None,
        description="Structured file in CSV or JSON format",
    ),
    unstructured_files: List[UploadFile] = File(
        default=[],
        description="Unstructured PDF invoice files",
    ),
    db: Session = Depends(get_db),
):
    """
    Ingest financial files and compute baseline metrics.
    
    This endpoint:
    1. Accepts CSV/JSON for transaction history
    2. Accepts PDF files for invoice extraction
    3. Normalizes and cleans data using pandas
    4. Calculates financial metrics (current_ratio, quick_ratio, burn_rate)
    5. Stores data in database
    6. Returns baseline metrics for BNPL analysis
    """
    company = CompanyService.get_company(db, sme_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if structured_file is None and len(unstructured_files) == 0:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one structured file or unstructured PDF file",
        )

    inserted_transactions = 0
    processed_documents = 0
    all_transactions = []

    try:
        # Process structured file (CSV/JSON)
        if structured_file is not None:
            content = await structured_file.read()
            filename = (structured_file.filename or "").lower()

            if filename.endswith(".csv"):
                df = pd.read_csv(BytesIO(content))
            elif filename.endswith(".json"):
                df = pd.read_json(BytesIO(content))
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Structured file must be .csv or .json",
                )

            normalized_df = _normalize_transaction_dataframe(df)
            records = normalized_df.to_dict(orient="records")

            for row in records:
                tx = Transaction(
                    company_id=sme_id,
                    transaction_date=row["transaction_date"],
                    transaction_type=row["transaction_type"],
                    amount=float(row["amount"]),
                    description=str(row.get("description") or ""),
                    counterparty=str(row.get("counterparty") or ""),
                    category=str(row.get("category") or "other"),
                    reference_number=row.get("reference_number"),
                )
                db.add(tx)
                all_transactions.append(row)
                inserted_transactions += 1

        # Process unstructured files (PDF invoices)
        for uploaded in unstructured_files:
            file_name = uploaded.filename or "unknown.pdf"
            if not file_name.lower().endswith(".pdf"):
                continue

            pdf_bytes = await uploaded.read()
            reader = PdfReader(BytesIO(pdf_bytes))
            raw_text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
            extracted = DataProcessor.extract_invoice_data(raw_text)

            document = FinancialDocument(
                company_id=sme_id,
                document_type=DocumentType.INVOICE,
                document_name=file_name,
                file_path=f"uploaded://{file_name}",
                amount=extracted.get("amount"),
                counterparty=extracted.get("vendor"),
                extracted_data=extracted,
                raw_content=raw_text,
                processing_status="processed",
            )
            db.add(document)
            processed_documents += 1
            
            # Add as transaction if amount extracted
            if extracted.get("amount"):
                tx = Transaction(
                    company_id=sme_id,
                    transaction_date=extracted.get("date", datetime.utcnow()),
                    transaction_type="purchase",
                    amount=float(extracted.get("amount", 0)),
                    description=f"Invoice from {extracted.get('vendor', 'Unknown')}",
                    counterparty=extracted.get("vendor", "Unknown"),
                    category="invoice",
                    reference_number=extracted.get("invoice_number"),
                )
                db.add(tx)
                all_transactions.append({
                    "transaction_date": tx.transaction_date,
                    "transaction_type": tx.transaction_type,
                    "amount": tx.amount,
                    "category": tx.category,
                })
                inserted_transactions += 1

        db.commit()

        # Calculate comprehensive financial metrics
        if all_transactions:
            metrics = FinancialMetricsCalculator.calculate_metrics(
                transactions=all_transactions,
                current_assets=company.annual_revenue / 12 * 2 if company.annual_revenue else None,
                current_liabilities=company.annual_revenue / 12 if company.annual_revenue else None,
                period_days=90,
            )
            
            health_assessment = FinancialMetricsCalculator.classify_financial_health(metrics)
            
            # Update company with calculated runway
            if metrics.get("monthly_burn_rate", 0) > 0:
                runway_days = (company.annual_revenue / 12 * 3) / metrics["monthly_burn_rate"] * 30 if company.annual_revenue else 90
                company.cash_flow_runway_days = min(int(runway_days), 365)
            
            db.commit()
        else:
            metrics = {}
            health_assessment = {}

        return {
            "sme_id": sme_id,
            "status": "processed",
            "records_stored": {
                "transactions_inserted": inserted_transactions,
                "documents_processed": processed_documents,
            },
            "metrics": _sanitize_for_json(metrics),
            "health_assessment": _sanitize_for_json(health_assessment),
            "next_steps": [
                "Review financial metrics above",
                "Submit a purchase order to evaluate BNPL options",
                "Monitor cash runway for strategic financing",
            ]
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Financial ingestion failed: {str(exc)}")


@router.post(
    "/{company_id}/transactions",
    response_model=TransactionResponse,
    summary="Record Single Transaction",
    description="Record a single financial transaction",
)
async def record_transaction(
    company_id: int,
    transaction_data: TransactionCreate,
    db: Session = Depends(get_db),
) -> TransactionResponse:
    """Record a single transaction for a company"""
    # Validate company exists
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Ensure company_id matches
    transaction_data.company_id = company_id
    transaction = TransactionService.create_transaction(db, transaction_data)
    return transaction


@router.post(
    "/{company_id}/transactions/bulk",
    response_model=List[TransactionResponse],
    summary="Bulk Upload Transactions",
    description="Import multiple financial transactions at once",
)
async def bulk_upload_transactions(
    company_id: int,
    bulk_data: TransactionBulkCreate,
    db: Session = Depends(get_db),
) -> List[TransactionResponse]:
    """
    Bulk upload transactions for a company
    
    Useful for importing historical data from accounting systems
    """
    # Validate company exists
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Override company_id to ensure data integrity
    bulk_data.company_id = company_id
    transactions = TransactionService.bulk_create_transactions(db, bulk_data)
    return transactions


@router.get(
    "/{company_id}/transactions",
    response_model=List[TransactionResponse],
    summary="Get Transaction History",
    description="Retrieve transaction history for a company",
)
async def get_transactions(
    company_id: int,
    days_back: int = Query(90, ge=1, le=365, description="Number of days to retrieve"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> List[TransactionResponse]:
    """Get transaction history for financial analysis"""
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    transactions = TransactionService.get_company_transactions(
        db,
        company_id,
        days_back=days_back,
        skip=skip,
        limit=limit
    )
    return transactions


@router.get(
    "/{company_id}/financial-summary",
    summary="Get Financial Summary",
    description="Get current financial metrics and health",
)
async def get_financial_summary(
    company_id: int,
    db: Session = Depends(get_db),
):
    """
    Get financial summary for a company
    
    Returns key metrics used in decision analysis
    """
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    metrics = CompanyService.calculate_financial_metrics(db, company_id)
    
    return {
        "company_id": company_id,
        "company_name": company.company_name,
        "industry": company.industry,
        "credit_score": company.credit_score,
        "financial_metrics": metrics,
    }


# ============ Data Management Endpoints ============

@router.delete(
    "/{company_id}/transactions/{transaction_id}",
    summary="Delete Transaction",
    description="Remove a transaction record",
)
async def delete_transaction(
    company_id: int,
    transaction_id: int,
    db: Session = Depends(get_db),
):
    """Delete a transaction record"""
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    success = TransactionService.delete_transaction(db, transaction_id, company_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {"status": "deleted", "transaction_id": transaction_id}
