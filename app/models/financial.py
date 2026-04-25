"""
Database models for Z.AI financial system
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db import Base


class CompanyProfile(Base):
    """SME/Company financial profile"""
    __tablename__ = "company_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), unique=True, index=True, nullable=False)
    registration_number = Column(String(50), unique=True, nullable=False)
    industry = Column(String(100), nullable=False)
    annual_revenue = Column(Float, nullable=True)
    employees_count = Column(Integer, nullable=True)
    credit_score = Column(Float, nullable=True)
    cash_flow_runway_days = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="company")
    financial_documents = relationship("FinancialDocument", back_populates="company")
    recommendations = relationship("BNPLRecommendation", back_populates="company")
    analysis_reports = relationship("AnalysisReport", back_populates="company")


class Transaction(Base):
    """Financial transaction records"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("company_profiles.id"), nullable=False, index=True)
    transaction_date = Column(DateTime, nullable=False, index=True)
    transaction_type = Column(String(50), nullable=False)  # "purchase", "sale", "payment", "receipt"
    amount = Column(Float, nullable=False)
    description = Column(String(500), nullable=True)
    counterparty = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)  # "inventory", "operations", "payroll", etc.
    reference_number = Column(String(100), nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("CompanyProfile", back_populates="transactions")


class DocumentType(str, enum.Enum):
    """Types of financial documents"""
    INVOICE = "invoice"
    CONTRACT = "contract"
    RECEIPT = "receipt"
    STATEMENT = "statement"
    LEDGER = "ledger"
    OTHER = "other"


class FinancialDocument(Base):
    """Structured and unstructured financial documents"""
    __tablename__ = "financial_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("company_profiles.id"), nullable=False, index=True)
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    document_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    document_date = Column(DateTime, nullable=True)
    amount = Column(Float, nullable=True)
    counterparty = Column(String(255), nullable=True)
    extracted_data = Column(JSON, nullable=True)  # Extracted structured data from unstructured docs
    raw_content = Column(Text, nullable=True)  # Raw OCR/text extraction
    processing_status = Column(String(50), default="pending")  # "pending", "processed", "failed"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("CompanyProfile", back_populates="financial_documents")


class BNPLRecommendation(Base):
    """BNPL and financing recommendations from GLM"""
    __tablename__ = "bnpl_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("company_profiles.id"), nullable=False, index=True)
    recommendation_type = Column(String(50), nullable=False)  # "bnpl", "traditional", "hybrid"
    transaction_amount = Column(Float, nullable=False)
    transaction_purpose = Column(String(200), nullable=False)  # "inventory", "operations", etc.
    
    # Recommendation Details
    recommendation_rationale = Column(Text, nullable=False)  # Why GLM recommends this
    estimated_interest_savings = Column(Float, nullable=True)
    estimated_cash_flow_improvement = Column(Float, nullable=True)
    revenue_capacity_increase = Column(Float, nullable=True)
    
    # BNPL Specific
    recommended_tenor_days = Column(Integer, nullable=True)
    payment_schedule = Column(JSON, nullable=True)
    
    # Traditional Financing Alternative
    alternative_option = Column(String(200), nullable=True)
    alternative_rationale = Column(Text, nullable=True)
    
    # Confidence and Status
    confidence_score = Column(Float, nullable=True)  # 0-1
    is_approved = Column(Boolean, default=False)
    implementation_status = Column(String(50), default="pending")  # "pending", "approved", "rejected", "implemented"
    
    glm_request_id = Column(String(255), nullable=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("CompanyProfile", back_populates="recommendations")


class AnalysisReport(Base):
    """Comprehensive financial analysis reports"""
    __tablename__ = "analysis_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("company_profiles.id"), nullable=False, index=True)
    report_type = Column(String(50), nullable=False)  # "financial_health", "cash_flow", "financing_strategy"
    
    # Financial Metrics
    revenue_trend = Column(JSON, nullable=True)
    expense_trend = Column(JSON, nullable=True)
    cash_balance = Column(Float, nullable=True)
    current_liabilities = Column(Float, nullable=True)
    total_debt = Column(Float, nullable=True)
    
    # Calculated Ratios
    debt_to_equity = Column(Float, nullable=True)
    current_ratio = Column(Float, nullable=True)
    quick_ratio = Column(Float, nullable=True)
    revenue_growth_rate = Column(Float, nullable=True)
    
    # Analysis Summary
    executive_summary = Column(Text, nullable=True)
    key_findings = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    
    # Report Metadata
    analysis_period_start = Column(DateTime, nullable=True)
    analysis_period_end = Column(DateTime, nullable=True)
    generated_by_glm = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("CompanyProfile", back_populates="analysis_reports")
