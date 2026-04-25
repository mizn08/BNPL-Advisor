"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class DocumentTypeSchema(str, Enum):
    """Document types"""
    INVOICE = "invoice"
    CONTRACT = "contract"
    RECEIPT = "receipt"
    STATEMENT = "statement"
    LEDGER = "ledger"
    OTHER = "other"


# ============ Company Profile Schemas ============

class CompanyProfileBase(BaseModel):
    """Base company profile schema"""
    company_name: str
    registration_number: str
    industry: str
    annual_revenue: Optional[float] = None
    employees_count: Optional[int] = None


class CompanyProfileCreate(CompanyProfileBase):
    """Schema for creating a company profile"""
    pass


class CompanyProfileUpdate(BaseModel):
    """Schema for updating company profile"""
    company_name: Optional[str] = None
    industry: Optional[str] = None
    annual_revenue: Optional[float] = None
    employees_count: Optional[int] = None


class CompanyProfileResponse(CompanyProfileBase):
    """Response schema for company profile"""
    id: int
    credit_score: Optional[float] = None
    cash_flow_runway_days: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============ Transaction Schemas ============

class TransactionBase(BaseModel):
    """Base transaction schema"""
    transaction_date: datetime
    transaction_type: str  # "purchase", "sale", "payment", "receipt"
    amount: float
    description: Optional[str] = None
    counterparty: Optional[str] = None
    category: Optional[str] = None
    reference_number: Optional[str] = None


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction"""
    company_id: int


class TransactionResponse(TransactionBase):
    """Response schema for transaction"""
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TransactionBulkCreate(BaseModel):
    """Schema for bulk uploading transactions"""
    company_id: int
    transactions: List[TransactionBase]


# ============ Financial Document Schemas ============

class FinancialDocumentBase(BaseModel):
    """Base financial document schema"""
    document_type: DocumentTypeSchema
    document_name: str
    document_date: Optional[datetime] = None
    amount: Optional[float] = None
    counterparty: Optional[str] = None


class FinancialDocumentCreate(FinancialDocumentBase):
    """Schema for creating a financial document"""
    company_id: int


class FinancialDocumentResponse(FinancialDocumentBase):
    """Response schema for financial document"""
    id: int
    company_id: int
    file_path: str
    extracted_data: Optional[Dict[str, Any]] = None
    processing_status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============ BNPL Recommendation Schemas ============

class BNPLRecommendationBase(BaseModel):
    """Base BNPL recommendation schema"""
    recommendation_type: str  # "bnpl", "traditional", "hybrid"
    transaction_amount: float
    transaction_purpose: str


class BNPLRecommendationCreate(BNPLRecommendationBase):
    """Schema for creating a BNPL recommendation"""
    company_id: int
    analysis_data: Optional[Dict[str, Any]] = None  # Data to pass to GLM


class BNPLRecommendationResponse(BNPLRecommendationBase):
    """Response schema for BNPL recommendation"""
    id: int
    company_id: int
    recommendation_rationale: str
    estimated_interest_savings: Optional[float] = None
    estimated_cash_flow_improvement: Optional[float] = None
    revenue_capacity_increase: Optional[float] = None
    recommended_tenor_days: Optional[int] = None
    alternative_option: Optional[str] = None
    confidence_score: Optional[float] = None
    is_approved: bool
    implementation_status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BNPLApprovalRequest(BaseModel):
    """Schema for approving a BNPL recommendation"""
    recommendation_id: int
    approved: bool
    approval_notes: Optional[str] = None


# ============ Analysis Report Schemas ============

class AnalysisReportBase(BaseModel):
    """Base analysis report schema"""
    report_type: str  # "financial_health", "cash_flow", "financing_strategy"
    analysis_period_start: datetime
    analysis_period_end: datetime


class AnalysisReportCreate(AnalysisReportBase):
    """Schema for creating an analysis report"""
    company_id: int


class AnalysisReportResponse(AnalysisReportBase):
    """Response schema for analysis report"""
    id: int
    company_id: int
    executive_summary: Optional[str] = None
    key_findings: Optional[Dict[str, Any]] = None
    recommendations: Optional[Dict[str, Any]] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    revenue_growth_rate: Optional[float] = None
    generated_by_glm: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============ GLM Request/Response Schemas ============

class GLMAnalysisRequest(BaseModel):
    """Schema for requesting GLM analysis"""
    company_id: int
    transaction_amount: float
    transaction_purpose: str
    current_cash_balance: float
    monthly_revenue: float
    monthly_expenses: float
    current_debt: Optional[float] = None
    credit_score: Optional[float] = None
    additional_context: Optional[Dict[str, Any]] = None


class GLMRecommendationResponse(BaseModel):
    """Schema for GLM recommendation response"""
    recommendation_type: str
    recommendation_rationale: str
    estimated_interest_savings: Optional[float] = None
    estimated_cash_flow_improvement: Optional[float] = None
    revenue_capacity_increase: Optional[float] = None
    recommended_tenor_days: Optional[int] = None
    payment_schedule: Optional[Dict[str, Any]] = None
    confidence_score: float
    alternative_option: Optional[str] = None
    alternative_rationale: Optional[str] = None


# ============ Health Check Schemas ============

class HealthCheckResponse(BaseModel):
    """Response schema for health check"""
    status: str
    version: str
    database: str
    timestamp: datetime


# Structured module exports for the target architecture layout
from .sme_schema import SMEProfileCreate as NewSMEProfileCreate
from .sme_schema import SMEProfileResponse as NewSMEProfileResponse
from .decision_schema import DecisionRequest
from .decision_schema import DecisionResponse
from .decision_schema import DecisionImpactMetrics
