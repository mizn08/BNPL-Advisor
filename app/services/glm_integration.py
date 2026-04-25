"""
Z.AI GLM API Integration
Core decision engine for financial recommendations
"""
import httpx
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.config import settings
from app.schemas import GLMAnalysisRequest, GLMRecommendationResponse

logger = logging.getLogger(__name__)


class GLMClient:
    """Client for interacting with Z.AI's GLM API"""
    
    def __init__(self):
        self.api_url = settings.ZAI_GLM_API_URL
        self.api_key = settings.ZAI_GLM_API_KEY
        self.model = settings.ZAI_GLM_MODEL
        self.timeout = settings.ZAI_GLM_TIMEOUT
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def analyze_financing_decision(
        self,
        request: GLMAnalysisRequest,
        company_name: str,
        industry: str,
    ) -> GLMRecommendationResponse:
        """
        Call Z.AI's GLM to analyze financing decision
        This is the CRITICAL PATH for decision intelligence
        
        Args:
            request: Financial analysis request
            company_name: Name of the company
            industry: Industry of the company
            
        Returns:
            GLM recommendation with decision rationale
            
        Raises:
            Exception: If GLM API call fails
        """
        
        # Prepare the prompt for GLM
        prompt = self._build_analysis_prompt(
            request=request,
            company_name=company_name,
            industry=industry,
        )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_url}/analyze",
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "company_id": request.company_id,
                        "analysis_type": "bnpl_vs_traditional_financing",
                        "temperature": 0.3,  # Lower temperature for consistent financial advice
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Parse GLM response
                recommendation = self._parse_glm_response(result)
                
                logger.info(
                    f"GLM analysis completed for company_id={request.company_id}, "
                    f"recommendation_type={recommendation.recommendation_type}"
                )
                
                return recommendation
                
        except httpx.HTTPError as e:
            logger.error(f"GLM API error: {str(e)}")
            raise Exception(f"Failed to get GLM recommendation: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GLM response: {str(e)}")
            raise Exception(f"Invalid GLM response format: {str(e)}")
    
    def _build_analysis_prompt(
        self,
        request: GLMAnalysisRequest,
        company_name: str,
        industry: str,
    ) -> str:
        """Build the prompt for GLM analysis"""
        
        cash_runway = (
            request.current_cash_balance / (request.monthly_expenses or 1)
            if request.monthly_expenses > 0
            else 0
        )
        
        profit_margin = (
            ((request.monthly_revenue - request.monthly_expenses) / request.monthly_revenue * 100)
            if request.monthly_revenue > 0
            else 0
        )
        
        prompt = f"""
You are an expert financial advisor for SMEs. Analyze this financing decision and recommend the best strategy.

COMPANY PROFILE:
- Name: {company_name}
- Industry: {industry}
- Credit Score: {request.credit_score or 'Not available'}

CURRENT FINANCIAL HEALTH:
- Monthly Revenue: RM {request.monthly_revenue:,.2f}
- Monthly Expenses: RM {request.monthly_expenses:,.2f}
- Profit Margin: {profit_margin:.1f}%
- Current Cash Balance: RM {request.current_cash_balance:,.2f}
- Cash Runway: {cash_runway:.1f} days
- Current Debt: RM {request.current_debt or 0:,.2f}

FINANCING REQUEST:
- Amount Needed: RM {request.transaction_amount:,.2f}
- Purpose: {request.transaction_purpose}

DECISION FRAMEWORK:
Compare BNPL (Buy Now, Pay Later) vs Traditional Financing:

1. BNPL PROS:
   - Faster approval and funding
   - Flexible payment terms (typically 30-90 days)
   - No collateral required
   - Good for maintaining cash flow
   - Ideal for specific purchases (inventory, equipment)

2. BNPL CONS:
   - Higher interest rates (typically 8-15% APR)
   - Smaller loan amounts typical
   - Limited to specific vendors/categories

3. TRADITIONAL FINANCING PROS:
   - Lower interest rates (4-8% APR)
   - Larger amounts available
   - Longer repayment terms
   - Builds credit history

4. TRADITIONAL FINANCING CONS:
   - Longer approval process (5-15 days)
   - Stricter credit requirements
   - Collateral often required
   - Higher documentation burden

YOUR TASK:
Based on the financial health metrics, recommend EITHER "bnpl", "traditional", or "hybrid".

Provide your response in this JSON format:
{{
    "recommendation_type": "bnpl" | "traditional" | "hybrid",
    "recommendation_rationale": "Clear explanation of why this recommendation suits this company",
    "estimated_interest_savings": numeric value or null,
    "estimated_cash_flow_improvement": numeric value or null,
    "revenue_capacity_increase": numeric value or null,
    "recommended_tenor_days": number or null,
    "payment_schedule": object with suggested payment dates or null,
    "confidence_score": 0.0 to 1.0,
    "alternative_option": "alternative recommendation" or null,
    "alternative_rationale": "why alternative might be considered" or null
}}

CRITICAL REQUIREMENTS:
- Explain WHY this recommendation is best for their cash flow
- Quantify the financial impact
- Consider their specific cash runway and profit margin
- Be specific about payment terms that would work
- Provide a clear alternative in case primary recommendation isn't feasible
"""
        
        if request.additional_context:
            prompt += f"\n\nADDITIONAL CONTEXT:\n{json.dumps(request.additional_context, indent=2)}"
        
        return prompt
    
    def _parse_glm_response(self, glm_response: Dict[str, Any]) -> GLMRecommendationResponse:
        """Parse GLM response into structured recommendation"""
        
        # Extract the recommendation from GLM response
        # The actual structure depends on Z.AI's GLM API response format
        recommendation_data = glm_response.get("recommendation", {})
        
        return GLMRecommendationResponse(
            recommendation_type=recommendation_data.get("recommendation_type", "hybrid"),
            recommendation_rationale=recommendation_data.get("recommendation_rationale", ""),
            estimated_interest_savings=recommendation_data.get("estimated_interest_savings"),
            estimated_cash_flow_improvement=recommendation_data.get("estimated_cash_flow_improvement"),
            revenue_capacity_increase=recommendation_data.get("revenue_capacity_increase"),
            recommended_tenor_days=recommendation_data.get("recommended_tenor_days"),
            payment_schedule=recommendation_data.get("payment_schedule"),
            confidence_score=recommendation_data.get("confidence_score", 0.7),
            alternative_option=recommendation_data.get("alternative_option"),
            alternative_rationale=recommendation_data.get("alternative_rationale"),
        )


# Singleton instance
glm_client = GLMClient()


async def get_glm_recommendation(
    request: GLMAnalysisRequest,
    company_name: str,
    industry: str,
) -> GLMRecommendationResponse:
    """
    Get BNPL vs Traditional Financing recommendation from GLM
    
    This function should be called whenever you need the GLM's decision
    on whether to recommend BNPL or traditional financing for a purchase.
    """
    return await glm_client.analyze_financing_decision(
        request=request,
        company_name=company_name,
        industry=industry,
    )
