"""Utility functions"""
import json
from typing import Dict, Any


def format_currency(amount: float, currency: str = "RM") -> str:
    """Format amount as currency"""
    return f"{currency} {amount:,.2f}"


def parse_json_response(response_text: str) -> Dict[str, Any]:
    """Parse JSON from response text"""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response_text[start:end])
        raise


def calculate_days_of_runway(cash_balance: float, daily_burn: float) -> int:
    """Calculate cash runway in days"""
    if daily_burn <= 0:
        return 999999  # Infinite runway if no burn
    return int(cash_balance / daily_burn)


def calculate_profit_margin(revenue: float, expenses: float) -> float:
    """Calculate profit margin percentage"""
    if revenue == 0:
        return 0
    return ((revenue - expenses) / revenue) * 100
