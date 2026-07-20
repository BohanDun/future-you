"""Core financial calculations from the Future You MVP specification."""

from decimal import ROUND_CEILING
from typing import Literal

from app.financial.money import MoneyInput, money, non_negative

Frequency = Literal["weekly", "monthly", "yearly"]


def calculate_monthly_cash_flow(
    monthly_income: MoneyInput,
    monthly_expenses: MoneyInput,
):
    income = non_negative(monthly_income, name="monthly income")
    expenses = non_negative(monthly_expenses, name="monthly expenses")
    return money(income - expenses)


def calculate_goal_completion_months(
    target: MoneyInput,
    current: MoneyInput,
    monthly_contribution: MoneyInput,
) -> int | None:
    goal_target = non_negative(target, name="goal target")
    current_savings = non_negative(current, name="current goal savings")
    contribution = non_negative(
        monthly_contribution,
        name="monthly contribution",
    )
    remaining = goal_target - current_savings

    if remaining <= 0:
        return 0
    if contribution == 0:
        return None

    return int((remaining / contribution).to_integral_value(rounding=ROUND_CEILING))


def apply_one_time_purchase(
    current_balance: MoneyInput,
    purchase_amount: MoneyInput,
):
    balance = non_negative(current_balance, name="current balance")
    purchase = non_negative(purchase_amount, name="purchase amount")
    return money(balance - purchase)


def convert_to_monthly(amount: MoneyInput, frequency: Frequency):
    value = non_negative(amount)
    if frequency == "weekly":
        return money(value * 52 / 12)
    if frequency == "monthly":
        return money(value)
    if frequency == "yearly":
        return money(value / 12)
    raise ValueError(f"Unsupported frequency: {frequency}")


def apply_recurring_expense(
    monthly_cash_flow: MoneyInput,
    amount: MoneyInput,
    frequency: Frequency,
):
    cash_flow = money(monthly_cash_flow)
    monthly_extra_cost = convert_to_monthly(amount, frequency)
    return monthly_extra_cost, money(cash_flow - monthly_extra_cost)


def apply_extra_savings(
    monthly_goal_contribution: MoneyInput,
    amount: MoneyInput,
    frequency: Frequency,
):
    contribution = non_negative(
        monthly_goal_contribution,
        name="monthly goal contribution",
    )
    extra_monthly_savings = convert_to_monthly(amount, frequency)
    return extra_monthly_savings, money(contribution + extra_monthly_savings)
