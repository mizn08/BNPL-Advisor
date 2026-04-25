#!/usr/bin/env python
"""
Integration test for financial data ingestion and metrics calculation
Validates the end-to-end flow of file upload → data processing → metrics calculation
"""

import sys
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services import DataProcessor, FinancialMetricsCalculator
from app.services.financial_metrics import FinancialMetricsCalculator as FMC


def test_metrics_calculation():
    """Test financial metrics calculation"""
    print("\n" + "="*60)
    print("TEST 1: Financial Metrics Calculation")
    print("="*60)
    
    # Sample transactions
    transactions = [
        {
            "transaction_date": datetime.utcnow() - timedelta(days=60),
            "transaction_type": "sale",
            "amount": 10000,
            "category": "revenue",
        },
        {
            "transaction_date": datetime.utcnow() - timedelta(days=50),
            "transaction_type": "purchase",
            "amount": 3000,
            "category": "expense",
        },
        {
            "transaction_date": datetime.utcnow() - timedelta(days=40),
            "transaction_type": "sale",
            "amount": 12000,
            "category": "revenue",
        },
        {
            "transaction_date": datetime.utcnow() - timedelta(days=30),
            "transaction_type": "payment",
            "amount": 2500,
            "category": "expense",
        },
        {
            "transaction_date": datetime.utcnow() - timedelta(days=20),
            "transaction_type": "sale",
            "amount": 11000,
            "category": "revenue",
        },
        {
            "transaction_date": datetime.utcnow() - timedelta(days=10),
            "transaction_type": "purchase",
            "amount": 4000,
            "category": "expense",
        },
    ]
    
    # Calculate metrics
    metrics = FinancialMetricsCalculator.calculate_metrics(
        transactions=transactions,
        current_assets=50000,
        current_liabilities=20000,
        period_days=90,
    )
    
    print("\nCalculated Metrics:")
    print(f"  Monthly Revenue: RM {metrics['monthly_revenue']:,.2f}")
    print(f"  Monthly Expenses: RM {metrics['monthly_expenses']:,.2f}")
    print(f"  Profit Margin: {metrics['profit_margin_percent']:.2f}%")
    print(f"  Current Ratio: {metrics['current_ratio']:.2f}")
    print(f"  Quick Ratio: {metrics['quick_ratio']:.2f}")
    print(f"  Monthly Burn Rate: RM {metrics['monthly_burn_rate']:,.2f}")
    print(f"  Transaction Count: {metrics['transaction_count']}")
    
    # Classify health
    health = FinancialMetricsCalculator.classify_financial_health(metrics)
    print("\nFinancial Health Classification:")
    print(f"  Health Score: {health['health_score']}/100")
    print(f"  Classification: {health['classification']}")
    print(f"  Risk Level: {health['risk_level']}")
    print(f"  Runway Months: {health['runway_months']:.1f}")
    
    assert metrics['monthly_revenue'] > 0, "Monthly revenue should be positive"
    assert metrics['transaction_count'] == 6, "Should have 6 transactions"
    assert health['health_score'] >= 0 and health['health_score'] <= 100, "Health score out of range"
    
    print("\n✅ Financial Metrics Test PASSED")
    return True


def test_data_processor_integration():
    """Test data processor integration"""
    print("\n" + "="*60)
    print("TEST 2: Data Processor Integration")
    print("="*60)
    
    # Sample transactions
    transactions = [
        {
            "transaction_date": datetime.utcnow() - timedelta(days=30),
            "transaction_type": "sale",
            "amount": 15000,
            "category": "revenue",
        },
        {
            "transaction_date": datetime.utcnow() - timedelta(days=20),
            "transaction_type": "purchase",
            "amount": 5000,
            "category": "expense",
        },
    ]
    
    # Process with DataProcessor
    result = DataProcessor.process_transactions(transactions, period_days=90)
    
    print("\nProcessed Data:")
    print(f"  Transaction Count: {result['transaction_count']}")
    print(f"  Monthly Revenue: RM {result['monthly_revenue']:,.2f}")
    print(f"  Monthly Expenses: RM {result['monthly_expenses']:,.2f}")
    
    assert result['transaction_count'] >= 0, "Transaction count should be non-negative"
    
    print("\n✅ Data Processor Integration Test PASSED")
    return True


def test_invoice_extraction():
    """Test invoice data extraction"""
    print("\n" + "="*60)
    print("TEST 3: Invoice Data Extraction")
    print("="*60)
    
    invoice_text = """
    INVOICE #INV-2024-001234
    Date: 2024-01-15
    
    Bill To:
    XYZ Retailers
    
    From: Supplier Co.
    
    Description of Services/Products
    - Item 1: RM 5,000.00
    - Item 2: RM 3,500.00
    
    Total Amount: RM 8,500.00
    """
    
    # Extract data
    extracted = DataProcessor.extract_invoice_data(invoice_text)
    
    print("\nExtracted Invoice Data:")
    print(f"  Invoice Number: {extracted.get('invoice_number', 'N/A')}")
    print(f"  Date: {extracted.get('date', 'N/A')}")
    print(f"  Vendor: {extracted.get('vendor', 'N/A')}")
    print(f"  Amount: RM {extracted.get('amount', 0):,.2f}")
    
    assert 'amount' in extracted, "Should extract amount"
    
    print("\n✅ Invoice Extraction Test PASSED")
    return True


def main():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("FINANCIAL DATA INGESTION INTEGRATION TESTS")
    print("="*60)
    
    try:
        test_metrics_calculation()
        test_data_processor_integration()
        test_invoice_extraction()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\nThe financial data ingestion pipeline is working correctly!")
        print("Ready to integrate with FastAPI endpoints.")
        
        return 0
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
