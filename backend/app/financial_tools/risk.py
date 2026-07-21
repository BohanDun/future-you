"""Documented, deterministic risk rules for financial simulations."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.financial_tools.money import MoneyInput, as_decimal, non_negative

RiskLevel = Literal["Low", "Medium", "High"]


@dataclass(frozen=True)
class RiskAssessment:
    level: RiskLevel
    reasons: tuple[str, ...]


def assess_financial_risk(
    *,
    monthly_cash_flow_before: MoneyInput,
    monthly_cash_flow_after: MoneyInput,
    available_balance_after: MoneyInput,
    monthly_expenses: MoneyInput,
    max_goal_delay_months: int = 0,
    minimum_projected_balance: MoneyInput | None = None,
) -> RiskAssessment:
    """Classify risk using cash flow, reserve coverage, and goal delay.

    High risk: negative cash flow/balance, less than one month of expenses,
    or a goal delayed by six or more months.
    Medium risk: less than two months of expenses, cash flow falls by at
    least 50%, or a goal is delayed by two to five months.
    """
    before = as_decimal(monthly_cash_flow_before, name="cash flow before")
    after = as_decimal(monthly_cash_flow_after, name="cash flow after")
    balance = as_decimal(available_balance_after, name="available balance")
    expenses = non_negative(monthly_expenses, name="monthly expenses")

    high_reasons: list[str] = []
    medium_reasons: list[str] = []

    if after < 0:
        high_reasons.append("Monthly cash flow becomes negative.")
    if balance < 0:
        high_reasons.append("Available balance becomes negative.")
    if (
        minimum_projected_balance is not None
        and as_decimal(minimum_projected_balance) < 0
        and balance >= 0
    ):
        high_reasons.append("Available balance becomes negative during the projection.")
    if expenses > 0 and balance < expenses:
        high_reasons.append("Available balance covers less than one month of expenses.")
    if max_goal_delay_months >= 999:
        high_reasons.append("A financial goal can no longer progress.")
    elif max_goal_delay_months >= 6:
        high_reasons.append(
            f"A financial goal is delayed by {max_goal_delay_months} months."
        )

    if high_reasons:
        return RiskAssessment("High", tuple(high_reasons))

    if expenses > 0 and balance < expenses * 2:
        medium_reasons.append("Available balance covers less than two months of expenses.")
    if before > 0 and after <= before * Decimal("0.5"):
        medium_reasons.append("Monthly cash flow falls by at least 50%.")
    if 2 <= max_goal_delay_months < 6:
        medium_reasons.append(
            f"A financial goal is delayed by {max_goal_delay_months} months."
        )

    if medium_reasons:
        return RiskAssessment("Medium", tuple(medium_reasons))
    return RiskAssessment("Low", ("Cash flow and financial buffers remain healthy.",))
