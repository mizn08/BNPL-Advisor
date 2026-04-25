"""
Company and financial data management services
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.models import (
    CompanyProfile,
    Transaction,
    FinancialDocument,
    BNPLRecommendation,
    AnalysisReport,
)
from app.schemas import (
    CompanyProfileCreate,
    CompanyProfileUpdate,
    TransactionCreate,
    TransactionBulkCreate,
    FinancialDocumentCreate,
    BNPLRecommendationCreate,
    AnalysisReportCreate,
)

logger = logging.getLogger(__name__)


class CompanyService:
    """Service for managing company profiles"""
    
    @staticmethod
    def create_company(db: Session, company_data: CompanyProfileCreate) -> CompanyProfile:
        """Create a new company profile"""
        db_company = CompanyProfile(**company_data.model_dump())
        db.add(db_company)
        db.commit()
        db.refresh(db_company)
        logger.info(f"Created company profile: {db_company.id}")
        return db_company
    
    @staticmethod
    def get_company(db: Session, company_id: int) -> Optional[CompanyProfile]:
        """Get company by ID"""
        return db.query(CompanyProfile).filter(CompanyProfile.id == company_id).first()
    
    @staticmethod
    def get_company_by_name(db: Session, company_name: str) -> Optional[CompanyProfile]:
        """Get company by name"""
        return db.query(CompanyProfile).filter(CompanyProfile.company_name == company_name).first()
    
    @staticmethod
    def list_companies(db: Session, skip: int = 0, limit: int = 100) -> List[CompanyProfile]:
        """List all companies with pagination"""
        return db.query(CompanyProfile).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_company(
        db: Session,
        company_id: int,
        company_data: CompanyProfileUpdate,
    ) -> Optional[CompanyProfile]:
        """Update company profile"""
        db_company = db.query(CompanyProfile).filter(CompanyProfile.id == company_id).first()
        if not db_company:
            return None
        
        update_data = company_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_company, field, value)
        
        db_company.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_company)
        logger.info(f"Updated company profile: {company_id}")
        return db_company
    
    @staticmethod
    def calculate_financial_metrics(db: Session, company_id: int) -> dict:
        """Calculate key financial metrics for a company"""
        
        # Get last 90 days of transactions
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=90)
        
        transactions = db.query(Transaction).filter(
            Transaction.company_id == company_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        ).all()
        
        # Calculate totals
        revenue = sum(t.amount for t in transactions if t.transaction_type in ["sale", "receipt"])
        expenses = sum(t.amount for t in transactions if t.transaction_type in ["purchase", "payment"])
        
        # Calculate monthly averages
        days_in_period = 90
        months_in_period = days_in_period / 30
        
        monthly_revenue = revenue / months_in_period if months_in_period > 0 else 0
        monthly_expenses = expenses / months_in_period if months_in_period > 0 else 0
        
        # Get company profile for additional data
        company = CompanyService.get_company(db, company_id)
        if not company:
            return {}
        
        return {
            "monthly_revenue": monthly_revenue,
            "monthly_expenses": monthly_expenses,
            "monthly_profit": monthly_revenue - monthly_expenses,
            "profit_margin_percent": (
                ((monthly_revenue - monthly_expenses) / monthly_revenue * 100)
                if monthly_revenue > 0 else 0
            ),
            "annual_revenue": monthly_revenue * 12,
            "total_transactions_90_days": len(transactions),
        }


class TransactionService:
    """Service for managing transactions"""
    
    @staticmethod
    def create_transaction(db: Session, transaction_data: TransactionCreate) -> Transaction:
        """Create a new transaction"""
        db_transaction = Transaction(**transaction_data.model_dump())
        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
        logger.info(f"Created transaction: {db_transaction.id}")
        return db_transaction
    
    @staticmethod
    def bulk_create_transactions(
        db: Session,
        bulk_data: TransactionBulkCreate,
    ) -> List[Transaction]:
        """Bulk create transactions"""
        transactions = []
        for transaction_data in bulk_data.transactions:
            tx = Transaction(
                company_id=bulk_data.company_id,
                **transaction_data.model_dump()
            )
            db.add(tx)
            transactions.append(tx)
        
        db.commit()
        for tx in transactions:
            db.refresh(tx)
        
        logger.info(f"Bulk created {len(transactions)} transactions for company {bulk_data.company_id}")
        return transactions
    
    @staticmethod
    def get_company_transactions(
        db: Session,
        company_id: int,
        days_back: int = 90,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Transaction]:
        """Get transactions for a company"""
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        return db.query(Transaction).filter(
            Transaction.company_id == company_id,
            Transaction.transaction_date >= start_date,
        ).order_by(desc(Transaction.transaction_date)).offset(skip).limit(limit).all()
    
    @staticmethod
    def delete_transaction(
        db: Session,
        transaction_id: int,
        company_id: int,
    ) -> bool:
        """Delete a transaction"""
        tx = db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.company_id == company_id,
        ).first()
        
        if not tx:
            return False
        
        db.delete(tx)
        db.commit()
        logger.info(f"Deleted transaction {transaction_id}")
        return True


class RecommendationService:
    """Service for managing BNPL recommendations"""
    
    @staticmethod
    def create_recommendation(
        db: Session,
        company_id: int,
        recommendation_type: str,
        transaction_amount: float,
        transaction_purpose: str,
    ) -> BNPLRecommendation:
        """Create a new BNPL recommendation"""
        db_rec = BNPLRecommendation(
            company_id=company_id,
            recommendation_type=recommendation_type,
            transaction_amount=transaction_amount,
            transaction_purpose=transaction_purpose,
            recommendation_rationale="Pending GLM analysis",
        )
        db.add(db_rec)
        db.commit()
        db.refresh(db_rec)
        logger.info(f"Created recommendation: {db_rec.id}")
        return db_rec
    
    @staticmethod
    def update_recommendation_from_glm(
        db: Session,
        recommendation_id: int,
        glm_response: dict,
        glm_request_id: str = None,
    ) -> Optional[BNPLRecommendation]:
        """Update recommendation with GLM response"""
        db_rec = db.query(BNPLRecommendation).filter(
            BNPLRecommendation.id == recommendation_id
        ).first()
        
        if not db_rec:
            return None
        
        db_rec.recommendation_type = glm_response.get("recommendation_type", db_rec.recommendation_type)
        db_rec.recommendation_rationale = glm_response.get("recommendation_rationale", "")
        db_rec.estimated_interest_savings = glm_response.get("estimated_interest_savings")
        db_rec.estimated_cash_flow_improvement = glm_response.get("estimated_cash_flow_improvement")
        db_rec.revenue_capacity_increase = glm_response.get("revenue_capacity_increase")
        db_rec.recommended_tenor_days = glm_response.get("recommended_tenor_days")
        db_rec.payment_schedule = glm_response.get("payment_schedule")
        db_rec.alternative_option = glm_response.get("alternative_option")
        db_rec.alternative_rationale = glm_response.get("alternative_rationale")
        db_rec.confidence_score = glm_response.get("confidence_score", 0.7)
        db_rec.glm_request_id = glm_request_id
        db_rec.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_rec)
        logger.info(f"Updated recommendation {recommendation_id} with GLM response")
        return db_rec
    
    @staticmethod
    def get_recommendation(
        db: Session,
        recommendation_id: int,
    ) -> Optional[BNPLRecommendation]:
        """Get recommendation by ID"""
        return db.query(BNPLRecommendation).filter(
            BNPLRecommendation.id == recommendation_id
        ).first()
    
    @staticmethod
    def list_company_recommendations(
        db: Session,
        company_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[BNPLRecommendation]:
        """List recommendations for a company"""
        return db.query(BNPLRecommendation).filter(
            BNPLRecommendation.company_id == company_id,
        ).order_by(desc(BNPLRecommendation.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def approve_recommendation(
        db: Session,
        recommendation_id: int,
        approved: bool,
    ) -> Optional[BNPLRecommendation]:
        """Approve or reject a recommendation"""
        db_rec = db.query(BNPLRecommendation).filter(
            BNPLRecommendation.id == recommendation_id
        ).first()
        
        if not db_rec:
            return None
        
        db_rec.is_approved = approved
        db_rec.implementation_status = "approved" if approved else "rejected"
        db_rec.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_rec)
        logger.info(f"{'Approved' if approved else 'Rejected'} recommendation {recommendation_id}")
        return db_rec
