"""Deterministic financial tools owned by Person 2.

The package intentionally has no AWS, HTTP, or generative-AI dependencies.
"""

from app.financial_tools.calculations import (
    apply_extra_savings,
    apply_one_time_purchase,
    apply_recurring_expense,
    calculate_goal_completion_months,
    calculate_monthly_cash_flow,
    convert_to_monthly,
)
from app.financial_tools.insights import generate_dashboard_insights
from app.financial_tools.risk import RiskAssessment, assess_financial_risk

__all__ = [
    "RiskAssessment",
    "apply_extra_savings",
    "apply_one_time_purchase",
    "apply_recurring_expense",
    "assess_financial_risk",
    "calculate_goal_completion_months",
    "calculate_monthly_cash_flow",
    "convert_to_monthly",
    "generate_dashboard_insights",
]
