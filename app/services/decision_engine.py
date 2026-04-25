"""
Decision Engine
Orchestrates data preparation and GLM integration for BNPL recommendations
"""
import logging
from typing import Dict, Any, List, Optional
from app.services.data_processor import DataProcessor
from app.core.z_ai_client import get_glm_client
from app.db import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BNPLDecisionEngine:
    """Orchestrates BNPL vs Traditional Financing decisions using GLM"""
    
    def __init__(self):
        self.data_processor = DataProcessor()
        self.glm_client = get_glm_client()
    
    async def analyze_financing_decision(
        self,
        company_id: int,
        company_profile: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        cash_balance: float,
        transaction_amount: float,
        transaction_purpose: str,
        current_debt: float = 0,
        credit_score: float = 700,
    ) -> Dict[str, Any]:
        """
        Analyze financing decision through full pipeline:
        1. Process financial data
        2. Prepare analysis payload
        3. Call Z.AI GLM
        4. Return recommendation with rationale
        
        Args:
            company_id: Company identifier
            company_profile: Company information (name, industry, etc.)
            transactions: List of financial transactions
            cash_balance: Current cash balance
            transaction_amount: Amount needed for purchase
            transaction_purpose: Purpose of the purchase
            current_debt: Existing debt
            credit_score: Company credit score
            
        Returns:
            BNPL recommendation with decision rationale and impact analysis
        """
        
        try:
            logger.info(f"Starting financing analysis for company {company_id}")
            
            # Step 1: Process financial data
            logger.debug("Step 1: Processing financial data...")
            financial_metrics = self.data_processor.aggregate_company_metrics(
                company_id=company_id,
                transactions=transactions,
                cash_balance=cash_balance,
                debt=current_debt,
                credit_score=credit_score,
            )
            
            # Step 2: Prepare GLM analysis payload
            logger.debug("Step 2: Preparing analysis payload...")
            glm_payload = {
                **financial_metrics,
                "transaction_amount": transaction_amount,
                "transaction_purpose": transaction_purpose,
            }
            
            # Step 3: Call Z.AI GLM (CRITICAL PATH)
            logger.debug("Step 3: Calling Z.AI GLM...")
            glm_recommendation = await self.glm_client.get_bnpl_recommendation(
                financial_analysis=glm_payload,
                company_profile=company_profile,
            )
            
            # Step 4: Enrich recommendation with context
            logger.debug("Step 4: Enriching recommendation with context...")
            enriched_recommendation = {
                "company_id": company_id,
                "company_name": company_profile.get("company_name"),
                "transaction_amount": transaction_amount,
                "transaction_purpose": transaction_purpose,
                
                # GLM Recommendation
                "recommendation_type": glm_recommendation.get("recommendation_type"),
                "recommendation_rationale": glm_recommendation.get("recommendation_rationale"),
                "confidence_score": glm_recommendation.get("confidence_score", 0.7),
                
                # Financial Impact
                "estimated_interest_savings": glm_recommendation.get("estimated_interest_savings"),
                "estimated_cash_flow_improvement": glm_recommendation.get("estimated_cash_flow_improvement"),
                "revenue_capacity_increase": glm_recommendation.get("revenue_capacity_increase"),
                
                # Terms
                "recommended_tenor_days": glm_recommendation.get("recommended_tenor_days"),
                "payment_schedule": glm_recommendation.get("payment_schedule"),
                
                # Alternative
                "alternative_option": glm_recommendation.get("alternative_option"),
                "alternative_rationale": glm_recommendation.get("alternative_rationale"),
                
                # Risk & Success
                "key_risks": glm_recommendation.get("key_risks", []),
                "success_factors": glm_recommendation.get("success_factors", []),
                
                # Financial Context for Display
                "financial_context": {
                    "cash_runway_days": financial_metrics.get("cash_runway_days"),
                    "profit_margin_percent": financial_metrics.get("profit_margin_percent"),
                    "monthly_revenue": financial_metrics.get("monthly_revenue"),
                    "monthly_expenses": financial_metrics.get("monthly_expenses"),
                    "debt_to_equity": financial_metrics.get("debt_to_equity"),
                    "financial_health": financial_metrics.get("financial_health"),
                    "risk_level": financial_metrics.get("risk_level"),
                },
            }
            
            logger.info(
                f"Financing analysis complete: {glm_recommendation.get('recommendation_type')} "
                f"(confidence: {glm_recommendation.get('confidence_score', 0):.0%})"
            )
            
            return enriched_recommendation
            
        except Exception as e:
            logger.error(f"Error in financing analysis: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def evaluate_bnpl_suitability(
        financial_metrics: Dict[str, Any],
        transaction_amount: float,
    ) -> Dict[str, Any]:
        """
        Quick evaluation of BNPL suitability before GLM call
        Helps with decision pre-qualification
        
        Args:
            financial_metrics: Aggregated financial metrics
            transaction_amount: Amount needed
            
        Returns:
            Suitability assessment
        """
        
        cash_balance = financial_metrics.get("current_cash_balance", 0)
        monthly_revenue = financial_metrics.get("monthly_revenue", 0)
        profit_margin = financial_metrics.get("profit_margin_percent", 0)
        runway_months = financial_metrics.get("cash_runway_months", 0)
        
        # Quick suitability checks
        suitability_score = 0
        reasons = []
        
        # Check 1: Cash position relative to purchase
        if cash_balance < transaction_amount:
            suitability_score += 2
            reasons.append("Cash balance insufficient for full payment (BNPL advantage)")
        
        # Check 2: Healthy cash runway
        if runway_months >= 3:
            suitability_score += 1
            reasons.append("Adequate cash runway to support payment terms")
        elif runway_months < 1:
            suitability_score += 1
            reasons.append("Limited cash runway (BNPL flexibility beneficial)")
        
        # Check 3: Profitability
        if profit_margin > 15:
            suitability_score += 1
            reasons.append("Strong profitability supports flexible payments")
        
        # Check 4: Purchase size relative to revenue
        purchase_to_revenue_ratio = transaction_amount / (monthly_revenue or 1)
        if purchase_to_revenue_ratio < 1:
            suitability_score += 1
            reasons.append("Purchase size reasonable relative to monthly revenue")
        elif purchase_to_revenue_ratio > 2:
            suitability_score += 1
            reasons.append("Large purchase relative to revenue (BNPL spreads risk)")
        
        # Determine overall suitability
        if suitability_score >= 4:
            overall_suitability = "high"
        elif suitability_score >= 2:
            overall_suitability = "moderate"
        else:
            overall_suitability = "low"
        
        return {
            "suitability_score": suitability_score,
            "overall_suitability": overall_suitability,
            "reasons": reasons,
        }
    
    @staticmethod
    def format_recommendation_summary(
        recommendation: Dict[str, Any],
    ) -> str:
        """
        Format recommendation into human-readable summary
        
        Args:
            recommendation: Full recommendation from analyze_financing_decision
            
        Returns:
            Formatted text summary
        """
        
        summary = f"""
╔══════════════════════════════════════════════════════════════════╗
║           BNPL FINANCING RECOMMENDATION SUMMARY                  ║
╚══════════════════════════════════════════════════════════════════╝

COMPANY: {recommendation.get('company_name')}
TRANSACTION: RM {recommendation.get('transaction_amount', 0):,.2f} for {recommendation.get('transaction_purpose')}
RECOMMENDATION: {recommendation.get('recommendation_type', 'unknown').upper()}

RATIONALE:
{recommendation.get('recommendation_rationale', 'N/A')}

FINANCIAL IMPACT:
• Interest Savings: RM {recommendation.get('estimated_interest_savings', 0):,.2f}
• Cash Flow Improvement: RM {recommendation.get('estimated_cash_flow_improvement', 0):,.2f}
• Revenue Capacity Increase: {recommendation.get('revenue_capacity_increase', 0)}%

TERMS:
• Recommended Tenor: {recommendation.get('recommended_tenor_days', 'N/A')} days
• Confidence: {recommendation.get('confidence_score', 0):.0%}

FINANCIAL CONTEXT:
• Monthly Revenue: RM {recommendation.get('financial_context', {}).get('monthly_revenue', 0):,.2f}
• Profit Margin: {recommendation.get('financial_context', {}).get('profit_margin_percent', 0):.1f}%
• Cash Runway: {recommendation.get('financial_context', {}).get('cash_runway_days', 0)} days
• Financial Health: {recommendation.get('financial_context', {}).get('financial_health', 'unknown')}

KEY RISKS:
{chr(10).join(f'• {risk}' for risk in recommendation.get('key_risks', []))}

SUCCESS FACTORS:
{chr(10).join(f'• {factor}' for factor in recommendation.get('success_factors', []))}

ALTERNATIVE: {recommendation.get('alternative_option', 'N/A')}
{recommendation.get('alternative_rationale', '')}

══════════════════════════════════════════════════════════════════════
"""
        
        return summary
