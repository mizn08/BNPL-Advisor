"""
Pydantic schemas for file upload and financial data ingestion
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class DocumentTypeEnum(str, Enum):
    """Supported document types"""
    TRANSACTION_HISTORY = "transaction_history"
    INVOICE = "invoice"
    BANK_STATEMENT = "bank_statement"
    GENERAL = "general"


class FileUploadResponse(BaseModel):
    """Response from file upload"""
    id: str
    company_id: str
    filename: str
    document_type: str
    file_size_bytes: int
    transaction_count: int
    extracted_data: Dict[str, Any]
    stored_transactions: int
    status: str  # "success" or "partial"
    message: str
    metrics_summary: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class MetricsImportResponse(BaseModel):
    """Response with calculated metrics after import"""
    file_id: str
    company_id: str
    documents_processed: int
    total_transactions: int
    metrics: Dict[str, Any]
    health_assessment: Dict[str, Any]
    next_steps: List[str]


class TransactionBatchResponse(BaseModel):
    """Response from transaction batch upload"""
    count: int
    inserted: int
    skipped: int
    duplicates: int
    errors: List[Dict[str, str]]
    date_range: Optional[Dict[str, str]] = None
