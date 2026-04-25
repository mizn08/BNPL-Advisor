"""
Data Processor Service
Handles data cleaning, structuring, and transformation using pandas
Processes both structured and unstructured financial data
"""
import pandas as pd
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DataProcessor:
    """Processes and structures financial data for decision analysis"""
    
    @staticmethod
    def process_transactions(
        transactions: List[Dict[str, Any]],
        period_days: int = 90,
    ) -> Dict[str, Any]:
        """
        Process transaction data into financial metrics
        
        Args:
            transactions: List of transaction dictionaries
            period_days: Period to analyze (default 90 days)
            
        Returns:
            Dictionary with calculated financial metrics
        """
        try:
            # Convert to DataFrame for easier processing
            df = pd.DataFrame(transactions)
            
            if df.empty:
                logger.warning("No transactions provided for processing")
                return {
                    "monthly_revenue": 0,
                    "monthly_expenses": 0,
                    "cash_balance": 0,
                    "profit_margin_percent": 0,
                    "transaction_count": 0,
                }
            
            # Ensure transaction_date is datetime
            df['transaction_date'] = pd.to_datetime(df['transaction_date'])
            
            # Filter to period
            cutoff_date = datetime.utcnow() - timedelta(days=period_days)
            df = df[df['transaction_date'] >= cutoff_date]
            
            # Separate revenue and expenses
            revenue = df[df['transaction_type'].isin(['sale', 'receipt'])]['amount'].sum()
            expenses = df[df['transaction_type'].isin(['purchase', 'payment'])]['amount'].sum()
            
            # Calculate metrics
            months_in_period = period_days / 30
            monthly_revenue = revenue / months_in_period if months_in_period > 0 else 0
            monthly_expenses = expenses / months_in_period if months_in_period > 0 else 0
            monthly_profit = monthly_revenue - monthly_expenses
            
            profit_margin = (
                (monthly_profit / monthly_revenue * 100)
                if monthly_revenue > 0 else 0
            )
            
            # Calculate metrics by category
            category_analysis = df.groupby('category')['amount'].agg(['sum', 'count']).to_dict()
            
            metrics = {
                "period_days": period_days,
                "transaction_count": len(df),
                "monthly_revenue": monthly_revenue,
                "monthly_expenses": monthly_expenses,
                "monthly_profit": monthly_profit,
                "profit_margin_percent": profit_margin,
                "annual_revenue": monthly_revenue * 12,
                "total_revenue_period": revenue,
                "total_expenses_period": expenses,
                "revenue_to_expense_ratio": revenue / expenses if expenses > 0 else 0,
                "category_breakdown": category_analysis,
                "date_range": {
                    "start": df['transaction_date'].min().isoformat() if not df.empty else None,
                    "end": df['transaction_date'].max().isoformat() if not df.empty else None,
                }
            }
            
            logger.info(f"Processed {len(df)} transactions. Monthly revenue: RM {monthly_revenue:,.2f}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error processing transactions: {str(e)}")
            raise
    
    @staticmethod
    def extract_invoice_data(invoice_text: str) -> Dict[str, Any]:
        """
        Extract structured data from invoice text
        
        Args:
            invoice_text: Raw invoice text or OCR output
            
        Returns:
            Dictionary with extracted invoice data
        """
        try:
            extracted = {
                "invoice_number": None,
                "date": None,
                "amount": None,
                "vendor": None,
                "items": [],
                "payment_terms": None,
                "confidence": 0.0,
            }
            
            lines = invoice_text.split('\n')
            
            for line in lines:
                line_lower = line.lower()
                
                # Look for invoice number
                if 'invoice' in line_lower and extracted["invoice_number"] is None:
                    parts = line.split(':')
                    if len(parts) > 1:
                        extracted["invoice_number"] = parts[-1].strip()
                
                # Look for amounts
                if 'total' in line_lower or 'amount' in line_lower:
                    # Extract numbers from line
                    import re
                    amounts = re.findall(r'[\d,]+\.?\d*', line)
                    if amounts and extracted["amount"] is None:
                        extracted["amount"] = float(amounts[-1].replace(',', ''))
                
                # Look for dates
                if any(date_indicator in line_lower for date_indicator in ['date', 'invoice date', 'issued']):
                    extracted["date"] = line.split(':')[-1].strip() if ':' in line else None
            
            # Assign confidence based on data completeness
            fields_found = sum(1 for v in [
                extracted["invoice_number"],
                extracted["date"],
                extracted["amount"],
            ] if v is not None)
            extracted["confidence"] = fields_found / 3
            
            logger.info(f"Extracted invoice data with {fields_found}/3 key fields")
            return extracted
            
        except Exception as e:
            logger.error(f"Error extracting invoice data: {str(e)}")
            return {"error": str(e), "confidence": 0.0}
    
    @staticmethod
    def calculate_cash_runway(
        current_cash: float,
        monthly_expenses: float,
    ) -> Dict[str, Any]:
        """
        Calculate cash runway
        
        Args:
            current_cash: Current cash balance
            monthly_expenses: Monthly expense burn
            
        Returns:
            Cash runway metrics
        """
        if monthly_expenses <= 0:
            return {
                "runway_days": 999999,
                "runway_months": 999999,
                "status": "infinite",
                "risk_level": "low",
            }
        
        runway_days = current_cash / monthly_expenses * 30 if monthly_expenses > 0 else 0
        runway_months = runway_days / 30
        
        # Classify risk level
        if runway_months < 1:
            risk_level = "critical"
        elif runway_months < 3:
            risk_level = "high"
        elif runway_months < 6:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "runway_days": int(runway_days),
            "runway_months": round(runway_months, 1),
            "status": "healthy" if runway_months >= 6 else "at_risk",
            "risk_level": risk_level,
        }
    
    @staticmethod
    def aggregate_company_metrics(
        company_id: int,
        transactions: List[Dict[str, Any]],
        cash_balance: float,
        debt: float = 0,
        credit_score: float = 700,
    ) -> Dict[str, Any]:
        """
        Aggregate all metrics for decision analysis
        
        Args:
            company_id: Company identifier
            transactions: List of transactions
            cash_balance: Current cash
            debt: Current debt
            credit_score: Company credit score
            
        Returns:
            Comprehensive financial analysis
        """
        try:
            # Process transactions
            tx_metrics = DataProcessor.process_transactions(transactions)
            
            # Calculate cash runway
            runway = DataProcessor.calculate_cash_runway(
                current_cash=cash_balance,
                monthly_expenses=tx_metrics.get('monthly_expenses', 0),
            )
            
            # Calculate financial ratios
            monthly_revenue = tx_metrics.get('monthly_revenue', 0)
            monthly_expenses = tx_metrics.get('monthly_expenses', 0)
            
            # Debt-to-equity (simplified: using monthly revenue as equity proxy)
            debt_to_equity = debt / (monthly_revenue * 3) if monthly_revenue > 0 else 0
            
            # Current ratio (simplified)
            current_ratio = cash_balance / monthly_expenses if monthly_expenses > 0 else 0
            
            # Aggregate analysis
            metrics = {
                "company_id": company_id,
                "analysis_date": datetime.utcnow().isoformat(),
                
                # Revenue metrics
                "monthly_revenue": tx_metrics.get('monthly_revenue', 0),
                "monthly_expenses": tx_metrics.get('monthly_expenses', 0),
                "monthly_profit": tx_metrics.get('monthly_profit', 0),
                "profit_margin_percent": tx_metrics.get('profit_margin_percent', 0),
                
                # Cash metrics
                "current_cash_balance": cash_balance,
                "current_debt": debt,
                "cash_runway_days": runway.get('runway_days', 0),
                "cash_runway_months": runway.get('runway_months', 0),
                "cash_status": runway.get('status', 'unknown'),
                
                # Financial ratios
                "debt_to_equity": debt_to_equity,
                "current_ratio": current_ratio,
                "revenue_to_expense_ratio": tx_metrics.get('revenue_to_expense_ratio', 0),
                "credit_score": credit_score,
                
                # Transaction analysis
                "transaction_count_90d": tx_metrics.get('transaction_count', 0),
                "category_breakdown": tx_metrics.get('category_breakdown', {}),
                
                # Risk assessment
                "risk_level": runway.get('risk_level', 'unknown'),
                "financial_health": "strong" if tx_metrics.get('profit_margin_percent', 0) > 15 else (
                    "moderate" if tx_metrics.get('profit_margin_percent', 0) > 5 else "weak"
                ),
            }
            
            logger.info(f"Aggregated metrics for company {company_id}. Health: {metrics['financial_health']}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error aggregating metrics: {str(e)}")
            raise
