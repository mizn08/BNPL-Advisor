"""
Financial Metrics Calculation Service
Calculates key financial ratios and metrics from transaction data
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)


class FinancialMetricsCalculator:
    """Calculate financial metrics and ratios"""
    
    @staticmethod
    def calculate_metrics(
        transactions: List[Dict[str, Any]],
        current_assets: float = None,
        current_liabilities: float = None,
        period_days: int = 90,
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive financial metrics
        
        Args:
            transactions: List of transaction dictionaries
            current_assets: Current assets (for ratio calculations)
            current_liabilities: Current liabilities (for ratio calculations)
            period_days: Period to analyze
            
        Returns:
            Dictionary with calculated metrics
        """
        
        try:
            # Convert to DataFrame
            if not transactions:
                return FinancialMetricsCalculator._empty_metrics()
            
            df = pd.DataFrame(transactions)
            
            # Ensure transaction_date is datetime
            df['transaction_date'] = pd.to_datetime(df['transaction_date'])
            
            # Filter to period
            cutoff_date = datetime.utcnow() - timedelta(days=period_days)
            df_period = df[df['transaction_date'] >= cutoff_date]
            
            # Calculate revenue and expenses
            revenue = df_period[df_period['transaction_type'].isin(['sale', 'receipt'])]['amount'].sum()
            expenses = df_period[df_period['transaction_type'].isin(['purchase', 'payment'])]['amount'].sum()
            
            # Breakdown by category
            categories = df_period.groupby('category')['amount'].sum().to_dict()
            
            # Monthly metrics
            months_in_period = max(1, period_days / 30)
            monthly_revenue = revenue / months_in_period
            monthly_expenses = expenses / months_in_period
            monthly_profit = monthly_revenue - monthly_expenses
            
            # Profit margin
            profit_margin = (monthly_profit / monthly_revenue * 100) if monthly_revenue > 0 else 0
            
            # Current ratio (if liabilities provided)
            current_ratio = (current_assets / current_liabilities) if (current_assets and current_liabilities and current_liabilities > 0) else None
            
            # Quick ratio (assuming current_assets - inventory = 70% of assets)
            quick_assets = (current_assets * 0.7) if current_assets else None
            quick_ratio = (quick_assets / current_liabilities) if (quick_assets and current_liabilities and current_liabilities > 0) else None
            
            # Monthly burn rate (expenses)
            monthly_burn_rate = monthly_expenses
            
            # Transaction frequency
            daily_transactions = len(df_period) / max(1, period_days)
            
            # Volatility (standard deviation of transaction amounts)
            tx_amounts = df_period['amount'].values
            volatility = float(pd.Series(tx_amounts).std()) if len(tx_amounts) > 1 else 0
            
            metrics = {
                "period_days": period_days,
                "analysis_date": datetime.utcnow().isoformat(),
                
                # Revenue metrics
                "total_revenue": revenue,
                "total_expenses": expenses,
                "total_profit": revenue - expenses,
                "monthly_revenue": monthly_revenue,
                "monthly_expenses": monthly_expenses,
                "monthly_profit": monthly_profit,
                "profit_margin_percent": profit_margin,
                "annual_revenue_projection": monthly_revenue * 12,
                
                # Ratios
                "current_ratio": current_ratio,
                "quick_ratio": quick_ratio,
                "revenue_to_expense_ratio": (revenue / expenses) if expenses > 0 else 0,
                
                # Burn metrics
                "monthly_burn_rate": monthly_burn_rate,
                "daily_burn_rate": monthly_burn_rate / 30,
                
                # Transaction metrics
                "transaction_count": len(df_period),
                "daily_transaction_frequency": daily_transactions,
                "average_transaction_amount": df_period['amount'].mean() if len(df_period) > 0 else 0,
                "max_transaction_amount": df_period['amount'].max() if len(df_period) > 0 else 0,
                "min_transaction_amount": df_period['amount'].min() if len(df_period) > 0 else 0,
                "transaction_volatility": volatility,
                
                # Category breakdown
                "category_breakdown": categories,
                
                # Date range
                "date_range": {
                    "start": df_period['transaction_date'].min().isoformat() if len(df_period) > 0 else None,
                    "end": df_period['transaction_date'].max().isoformat() if len(df_period) > 0 else None,
                },
            }
            
            logger.info(f"Calculated metrics for {len(df_period)} transactions. Monthly revenue: {monthly_revenue:,.2f}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            raise
    
    @staticmethod
    def _empty_metrics() -> Dict[str, Any]:
        """Return empty metrics structure"""
        return {
            "period_days": 0,
            "analysis_date": datetime.utcnow().isoformat(),
            "total_revenue": 0,
            "total_expenses": 0,
            "total_profit": 0,
            "monthly_revenue": 0,
            "monthly_expenses": 0,
            "monthly_profit": 0,
            "profit_margin_percent": 0,
            "annual_revenue_projection": 0,
            "current_ratio": None,
            "quick_ratio": None,
            "revenue_to_expense_ratio": 0,
            "monthly_burn_rate": 0,
            "daily_burn_rate": 0,
            "transaction_count": 0,
            "daily_transaction_frequency": 0,
            "average_transaction_amount": 0,
            "max_transaction_amount": 0,
            "min_transaction_amount": 0,
            "transaction_volatility": 0,
            "category_breakdown": {},
            "date_range": {"start": None, "end": None},
        }
    
    @staticmethod
    def classify_financial_health(metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify company financial health based on metrics
        
        Args:
            metrics: Calculated financial metrics
            
        Returns:
            Health classification and risk assessment
        """
        
        profit_margin = metrics.get('profit_margin_percent', 0)
        current_ratio = metrics.get('current_ratio', 1)
        revenue_to_expense = metrics.get('revenue_to_expense_ratio', 0)
        transaction_volatility = metrics.get('transaction_volatility', 0)
        monthly_revenue = metrics.get('monthly_revenue', 0)
        monthly_burn = metrics.get('monthly_burn_rate', 0)
        
        # Calculate cash runway (simplified)
        if monthly_burn > 0 and monthly_revenue > 0:
            runway_months = monthly_revenue / monthly_burn
        else:
            runway_months = 12
        
        # Health score (0-100)
        health_score = 50
        
        # Profitability component (0-25)
        if profit_margin > 20:
            health_score += 25
        elif profit_margin > 10:
            health_score += 18
        elif profit_margin > 5:
            health_score += 12
        elif profit_margin > 0:
            health_score += 6
        
        # Liquidity component (0-25)
        if current_ratio and current_ratio > 2:
            health_score += 25
        elif current_ratio and current_ratio > 1.5:
            health_score += 18
        elif current_ratio and current_ratio > 1:
            health_score += 12
        elif current_ratio:
            health_score += 6
        
        # Revenue stability component (0-25)
        if transaction_volatility < monthly_revenue * 0.1:
            health_score += 25
        elif transaction_volatility < monthly_revenue * 0.2:
            health_score += 18
        elif transaction_volatility < monthly_revenue * 0.3:
            health_score += 12
        else:
            health_score += 6
        
        # Runway component (0-25)
        if runway_months > 12:
            health_score += 25
        elif runway_months > 6:
            health_score += 18
        elif runway_months > 3:
            health_score += 12
        elif runway_months > 1:
            health_score += 6
        
        # Classify health
        if health_score >= 85:
            classification = "excellent"
            risk_level = "very_low"
        elif health_score >= 70:
            classification = "good"
            risk_level = "low"
        elif health_score >= 55:
            classification = "fair"
            risk_level = "medium"
        elif health_score >= 40:
            classification = "poor"
            risk_level = "high"
        else:
            classification = "critical"
            risk_level = "very_high"
        
        return {
            "health_score": health_score,
            "classification": classification,
            "risk_level": risk_level,
            "runway_months": runway_months,
            "factors": {
                "profitability": f"{profit_margin:.1f}%",
                "liquidity": f"{current_ratio:.2f}" if current_ratio else "N/A",
                "revenue_to_expense": f"{revenue_to_expense:.2f}",
                "stability": "low" if transaction_volatility > monthly_revenue * 0.3 else "medium" if transaction_volatility > monthly_revenue * 0.1 else "high",
            }
        }
