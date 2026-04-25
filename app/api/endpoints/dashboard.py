"""
Dashboard endpoints for SME Advisor frontend.
Provides UI-focused aggregates and scenario projections.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CompanyProfile, Transaction
from app.services import CompanyService, TransactionService, FinancialMetricsCalculator

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


class ForecastScenarioRequest(BaseModel):
    monthly_revenue: float = Field(..., ge=0)
    fixed_expenses: float = Field(..., ge=0)
    expected_growth_rate: float = Field(0, ge=-100, le=200)
    loan_amount: float = Field(..., ge=0)
    repayment_term_months: int = Field(..., ge=1, le=60)
    interest_rate_percent: float = Field(0, ge=0, le=80)


def _tx_to_dict(tx: Transaction) -> Dict[str, Any]:
    return {
        "transaction_date": tx.transaction_date.isoformat() if tx.transaction_date else None,
        "transaction_type": tx.transaction_type,
        "amount": tx.amount,
        "description": tx.description,
        "counterparty": tx.counterparty,
        "category": tx.category,
    }


def _get_or_seed_default_company(db: Session) -> CompanyProfile:
    company = db.query(CompanyProfile).order_by(CompanyProfile.id.asc()).first()
    if company:
        return company

    seeded = CompanyProfile(
        company_name="SME Advisor Demo",
        registration_number="DEMO-2026-001",
        industry="Retail",
        annual_revenue=2940000.0,
        employees_count=14,
        credit_score=720,
        cash_flow_runway_days=95,
    )
    db.add(seeded)
    db.commit()
    db.refresh(seeded)

    now = datetime.utcnow()
    samples = [
        ("sale", 8400, "Client Payment - Vertex Inc", "revenue"),
        ("purchase", 3500, "WeWork Office Lease", "real_estate"),
        ("payment", 1240, "Amazon Web Services", "software"),
        ("purchase", 850, "IKEA Office Furniture", "equipment"),
        ("payment", 450, "Apple Store - MacBook Pro", "hardware"),
    ]
    for idx, (tx_type, amount, desc, category) in enumerate(samples):
        db.add(
            Transaction(
                company_id=seeded.id,
                transaction_date=now - timedelta(days=idx * 5),
                transaction_type=tx_type,
                amount=amount,
                description=desc,
                counterparty="",
                category=category,
            )
        )
    db.commit()
    return seeded


@router.get("/bootstrap")
def bootstrap_dashboard_data(db: Session = Depends(get_db)):
    """Returns a usable company id, creating demo data if needed."""
    company = _get_or_seed_default_company(db)
    return {
        "company_id": company.id,
        "company_name": company.company_name,
        "industry": company.industry,
    }


@router.get("/{company_id}/overview")
def get_dashboard_overview(company_id: int, db: Session = Depends(get_db)):
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    txs = TransactionService.get_company_transactions(
        db, company_id=company_id, days_back=180, skip=0, limit=2000
    )
    tx_dicts = [
        {
            "transaction_date": tx.transaction_date,
            "transaction_type": tx.transaction_type,
            "amount": tx.amount,
            "category": tx.category or "other",
        }
        for tx in txs
    ]
    metrics = FinancialMetricsCalculator.calculate_metrics(tx_dicts, period_days=180)
    health = FinancialMetricsCalculator.classify_financial_health(metrics)

    eapr = 18.0
    total_revenue = metrics.get("monthly_revenue", 0) * 6
    operating_cash = metrics.get("monthly_profit", 0)
    net_margin = metrics.get("profit_margin_percent", 0)

    return {
        "company": {
            "id": company.id,
            "name": company.company_name,
            "industry": company.industry,
            "credit_score": company.credit_score,
        },
        "kpis": {
            "total_revenue_mtd": round(total_revenue, 2),
            "operating_cash_flow": round(operating_cash, 2),
            "net_profit_margin_percent": round(net_margin, 2),
            "effective_annual_rate_percent": eapr,
        },
        "health_summary": {
            "classification": health.get("classification"),
            "risk_level": health.get("risk_level"),
            "health_score": health.get("health_score"),
            "summary": (
                f"Operational profile is {health.get('classification')} with "
                f"{metrics.get('monthly_revenue', 0):,.0f} monthly revenue run-rate."
            ),
        },
    }


@router.get("/{company_id}/transactions")
def get_dashboard_transactions(
    company_id: int,
    days_back: int = 30,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    txs = TransactionService.get_company_transactions(
        db, company_id=company_id, days_back=days_back, skip=0, limit=limit
    )
    return {
        "company_id": company_id,
        "items": [_tx_to_dict(tx) for tx in txs],
        "count": len(txs),
    }


@router.get("/{company_id}/benchmarks")
def get_dashboard_benchmarks(company_id: int, db: Session = Depends(get_db)):
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return {
        "market": "Malaysia",
        "providers": [
            {
                "provider": "Atome",
                "monthly_rate_percent": 1.5,
                "eapr_percent": 18.0,
                "late_fee_rm": 30.0,
                "typical_limit_rm": 5000,
                "fit": "Pure retail",
            },
            {
                "provider": "SPayLater",
                "monthly_rate_percent": 1.5,
                "eapr_percent": 18.0,
                "late_fee_rm": 10.0,
                "typical_limit_rm": 10000,
                "fit": "Shopee ecosystem",
            },
            {
                "provider": "TikTok Shop",
                "monthly_rate_percent": 1.5,
                "eapr_percent": 18.0,
                "late_fee_rm": 15.0,
                "typical_limit_rm": 8000,
                "fit": "Social commerce",
            },
            {
                "provider": "Grab PayLater",
                "monthly_rate_percent": 0.0,
                "eapr_percent": 0.0,
                "late_fee_rm": 10.0,
                "typical_limit_rm": 4000,
                "fit": "Quick conversion",
            },
        ],
    }


@router.post("/{company_id}/forecast")
def run_forecast(
    company_id: int,
    request: ForecastScenarioRequest,
    db: Session = Depends(get_db),
):
    company = CompanyService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    monthly_rate = request.interest_rate_percent / 100.0 / 12.0
    if monthly_rate > 0:
        monthly_payment = (
            request.loan_amount
            * monthly_rate
            / (1 - (1 + monthly_rate) ** (-request.repayment_term_months))
        )
    else:
        monthly_payment = request.loan_amount / max(request.repayment_term_months, 1)

    bars: List[Dict[str, Any]] = []
    revenue = request.monthly_revenue
    for idx in range(request.repayment_term_months):
        month_label = f"M{idx + 1}"
        expense = request.fixed_expenses + monthly_payment
        profit = revenue - expense
        bars.append(
            {
                "month": month_label,
                "revenue": round(revenue, 2),
                "expenses_plus_debt": round(expense, 2),
                "profit": round(profit, 2),
            }
        )
        revenue *= 1 + (request.expected_growth_rate / 100.0)

    avg_profit = sum(x["profit"] for x in bars) / max(len(bars), 1)
    projected_net_income = avg_profit * request.repayment_term_months

    return {
        "scenario": request.model_dump(),
        "monthly_payment": round(monthly_payment, 2),
        "projected_net_income": round(projected_net_income, 2),
        "series": bars,
    }
